from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
import warnings
from collections import defaultdict
import re
import xtgeo
app = FastAPI(title="Гидродинамический симулятор")
templates = Jinja2Templates(directory="templates")

# Подключаем папку static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Папка, где лежат include-файлы (задай нужный путь)
UPLOAD_DIR = "uploads"
PLOT_DIR = "static/plots"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)

# Глобальное хранилище
MODEL_STATE = {
    "current_model": None,
    "params": {},
    "files": [],          # найденные include
    "files_on_server": [], # реально загруженные include
    "grid_dict": {},
    "init_dict": {},
    'dimensions': [],
}

KEYWORDS_DATA = {
    "SPEC": "Определение сетки",
    "TITL": "Название модели",
    "IDAT": "Начальная дата моделирования",
    "SDAT": "Дата рестарта",
    "UNIT": "Система единиц",
    "MODE": "Режим входной обработки",
    "HORI": "Шаблон разностной схемы для расчетов в горизонтальной плоскости",
    "VERT": "Шаблон разностной схемы для расчетов в вертикальной плоскости",
    "CROC": "Cжимаемость породы",
    "REFE": "Давление приведения для сжимаемости",
}

KEYWORDS_INCLUDE = {
    "ACTN": "",
    "FIPN": "",
    "COOR": "",
    "ZCOR": "",
    "NTOG": "",
    "PORO": "",
    "K_X": "",
    "SWAT": "",
}

def get_model_dir(model_name: str) -> str:
    """Возвращает путь к папке модели, создаёт, если нет."""
    path = os.path.join(UPLOAD_DIR, model_name)
    os.makedirs(path, exist_ok=True)
    return path

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Получаем список реально загруженных файлов на сервере
    model_name = MODEL_STATE.get("current_model")
    if model_name:
        model_dir = get_model_dir(model_name)
        MODEL_STATE['files_on_server'] = os.listdir(model_dir)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "params": MODEL_STATE.get("params"),
            "files": MODEL_STATE.get('files'),  # изначально пусто, пока нет загруженной модели
            "files_on_server": MODEL_STATE.get('files_on_server'),
            "current_model": MODEL_STATE.get('current_model')
        }
    )

@app.get("/plot", response_class=HTMLResponse)
async def plot_view(request: Request):
    model_name = MODEL_STATE.get("current_model")
    if not model_name:
        return RedirectResponse(url="/", status_code=303)

    plot_urls = {}

    dimensions = MODEL_STATE.get('dimensions')
    nx = dimensions[0]
    ny = dimensions[1]
    nz = dimensions[2]
    grid_dict = MODEL_STATE['grid_dict']
    init_dict = MODEL_STATE['init_dict']

    # volume = compute_cell_geometry(grid_dict['COOR'], grid_dict['ZCOR'], NX, NY, NZ)
    # volume1d = volume.ravel()
    if len(grid_dict['VOLU']) and len(grid_dict['NTOG']) and len(grid_dict['PORO']) and len(init_dict['SOIL']):
        movable_oil = grid_dict['VOLU'] * grid_dict['NTOG'] * grid_dict['PORO'] * init_dict['SOIL']
    else:
        movable_oil = np.array([])

    plot_perm = plot_mean_map(grid_dict['K_X'], nx, ny, nz, 'k_x.png', 'мД')
    plot_poro = plot_mean_map(grid_dict['PORO'], nx, ny, nz, 'poro.png', 'д. ед.')
    plot_ntg = plot_mean_map(grid_dict['NTOG'], nx, ny, nz, 'ntg.png', 'д. ед.')
    plot_swat = plot_mean_map(init_dict['SWAT'],  nx, ny, nz,'swat.png','д. ед.', cmap='coolwarm', vmin=0, vmax=1)
    plot_soil = plot_mean_map(init_dict['SOIL'],  nx, ny, nz, 'soil.png', 'д. ед.', cmap='coolwarm', vmin=0, vmax=1)
    plot_vol = plot_mean_map(grid_dict['VOLU'], nx, ny, nz, 'volu.png', 'д. ед.')
    plot_movable_oil = plot_mean_map(movable_oil, nx, ny, nz, 'movable.png', 'д. ед.', operation='sum')

    plot_urls['Проницаемость'] = plot_perm
    plot_urls['Пористость'] = plot_poro
    plot_urls['NTG'] = plot_ntg
    plot_urls['Водонасыщенность'] = plot_swat
    plot_urls['Нефтенасыщенность'] = plot_soil
    plot_urls['Плотность подвижных запасов нефти'] = plot_movable_oil
    plot_urls['Объемы'] = plot_vol

    return templates.TemplateResponse(
        request,
        "plot.html",
        {
            "current_model": model_name,
            "files_on_server": MODEL_STATE.get("files_on_server"),
            "params": MODEL_STATE.get("params"),
            "plot_urls": plot_urls,
        }
    )

@app.get("/calculate", response_class=HTMLResponse)
async def calculate(request: Request):
    model_name = MODEL_STATE.get("current_model")
    model_dir = get_model_dir(model_name)
    list_of_files = os.listdir(model_dir)
    grid_name = [file for file in list_of_files if file.endswith(".mgrid")][0]
    init_name = [file for file in list_of_files if file.endswith(".minit")][0]
    # grid
    file_path = os.path.join(model_dir, grid_name)
    grid_list = file_read_to_list(file_path)
    grid_dict = file_processing(grid_list)
    MODEL_STATE["grid_dict"] = grid_dict
    # init
    file_path = os.path.join(model_dir, init_name)
    init_list = file_read_to_list(file_path)
    init_dict = file_processing(init_list)
    if len(init_dict['SWAT']):
        init_dict['SOIL'] = 1 - init_dict['SWAT']
    else:
        init_dict['SOIL'] = np.array([])
    MODEL_STATE["init_dict"] = init_dict

    specgrid = MODEL_STATE['params']['Определение сетки'][0].split()
    nx = int(specgrid[0])
    ny = int(specgrid[1])
    nz = int(specgrid[2])

    MODEL_STATE['dimensions'] = [nx, ny, nz]

    volume = compute_cell_geometry(grid_dict['COOR'], grid_dict['ZCOR'], nx, ny, nz)
    volume1d = volume.ravel()
    MODEL_STATE['grid_dict']['VOLU'] = volume1d
    return templates.TemplateResponse(
        request,
        "calculate.html",
        {
            "current_model": MODEL_STATE.get("current_model"),
            "params": MODEL_STATE.get("params"),
            "files_on_server": MODEL_STATE.get("files_on_server"),
            'grid': MODEL_STATE.get("grid_dict"),
            'init': MODEL_STATE.get("init_dict"),
        }
    )

@app.post("/delete_file")
async def delete_file(filename: str = Form(...)):
    model_name = MODEL_STATE.get("current_model")
    if not model_name:
        return RedirectResponse(url="/", status_code=303)
    model_dir = get_model_dir(model_name)
    file_path = os.path.join(model_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    MODEL_STATE["files_on_server"] = os.listdir(model_dir)
    return RedirectResponse(url="/", status_code=303)

@app.post("/upload_include")
async def upload_include(request: Request, include_name: str = Form(...), file: UploadFile = File(...)):
    model_name = MODEL_STATE.get("current_model")
    if not model_name:
        return RedirectResponse(url="/", status_code=303)
    model_dir = get_model_dir(model_name)
    # Сохраняем include
    saved_path = os.path.join(model_dir, file.filename)
    with open(saved_path, "wb") as buffer:
        buffer.write(await file.read())
    # Обновляем состояние
    MODEL_STATE["files_on_server"] = os.listdir(model_dir)
    # После загрузки возвращаемся на главную
    return RedirectResponse(url="/", status_code=303)
    # return templates.TemplateResponse(
    #     "index.html",
    #     {
    #         "request": request,
    #         "params": MODEL_STATE['params'],   # можно сюда подставить параметры модели, если нужно
    #         "files": MODEL_STATE['files'],  # показываем последний загруженный include
    #         "files_on_server": MODEL_STATE['files_on_server']
    #     }
    # )

@app.post("/upload", response_class=HTMLResponse)
async def upload_model(request: Request, file: UploadFile = File(...)):
    params = defaultdict(list)
    params['Имя файла'] = file.filename
    model_dir = get_model_dir(params['Имя файла'])
    files = []
    lines = []

    # Сохраняем основной файл
    main_file_path = os.path.join(model_dir, file.filename)
    with open(main_file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Читаем строки файла
    with open(main_file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]


    i = 0
    while i < len(lines):
        line = lines[i]
        separated_list = re.split(r'[:\s]+', line)
        if separated_list[0].upper()[:4] in KEYWORDS_DATA:
            if len(separated_list) == 1 and separated_list[0].upper()[:4] != 'TITL':
                flag = True
                while i + 1 < len(lines) and flag:
                    temp = lines[i + 1]
                    if temp.endswith("/"):
                        flag = False
                        temp = temp.strip("/")
                    params[KEYWORDS_DATA[separated_list[0].upper()[:4]]].append(temp)
                    i += 1
                i += 2
            elif len(separated_list) == 2 and separated_list[1].upper()[:4] in {"UNIF", "VARI", "TOPS"}:
                params[KEYWORDS_DATA[separated_list[0].upper()[:4]]].append(separated_list[1])
                flag = True
                while i + 1 < len(lines) and flag:
                    temp = lines[i + 1]
                    if temp.endswith("/"):
                        flag = False
                        temp = temp.strip("/")
                    params[KEYWORDS_DATA[separated_list[0].upper()[:4]]].append(temp)
                    i += 1
            else:
                if separated_list[1:] != [""]:
                    params[KEYWORDS_DATA[separated_list[0].upper()[:4]]] = separated_list[1:]
                i += 1
        elif separated_list[0].upper()[:4] == "INCL":
            include_file = lines[i + 1].strip("'")
            files.append(os.path.basename(include_file))
            i += 2
        else:
            i += 1

    MODEL_STATE["params"] = params
    MODEL_STATE["files"] = files
    MODEL_STATE["files_on_server"] = os.listdir(model_dir)
    MODEL_STATE["current_model"] = file.filename
    return RedirectResponse(url="/", status_code=303)
    # return templates.TemplateResponse(
    #     "index.html",
    #     {
    #         "request": request,
    #         "params": MODEL_STATE["params"],
    #         "files": MODEL_STATE["files"],
    #         "files_on_server": MODEL_STATE["files_on_server"]
    #     }
    # )

def file_read_to_list(file):
    file_list = []
    with open(file, 'r') as f:
        for line in f:
            if not line.startswith("--") and line != "\n":
                file_list.append(line)
    return file_list


def file_processing(file_list):
    file_dict = defaultdict(list)
    i = 0
    while i < len(file_list) - 1:
        if file_list[i][:4].strip() in KEYWORDS_INCLUDE:
            key_list = file_dict[file_list[i][:4].strip()]
            flag = True
            i += 1
            while flag:
                temp_str = file_list[i]
                if "/" in temp_str:
                    flag = False
                    temp_str = temp_str.strip("/")
                    i -= 1
                temp_list = temp_str.split()

                result = []
                for item in temp_list:
                    if '*' in item:
                        count, value = item.split('*')
                        result.extend([value] * int(count))
                    else:
                        result.append(item)

                temp_list = result
                if len(temp_list):
                    key_list.extend(temp_list)
                i += 1
        i += 1
    for key, value in file_dict.items():
        file_dict[key] = np.array(value, dtype=float)
    return file_dict

def plot_mean_map(
    values, nx, ny, nz,
    filename="mean_map.png",
    label="Среднее значение",
    cmap=None,    # цветовая палитра
    vmin=None, vmax=None,  # минимальное и максимальное значение для шкалы
    operation="mean",
):
    if len(values) == 0:
        return
    cube = values.reshape(nz, ny, nx)
    if operation == "mean":
        plot_map = cube.mean(axis=0)
    elif operation == "sum":
        plot_map = cube.sum(axis=0)

    plt.figure(figsize=(6, 5))
    im = plt.imshow(
        plot_map,
        origin="lower",
        aspect="auto",
        extent=[0, nx, 0, ny],
        cmap=cmap,
        vmin=vmin,
        vmax=vmax
    )
    plt.colorbar(im, label=label)
    plt.xlabel("X")
    plt.ylabel("Y")
    # plt.title("Карта средних значений по z")
    model_name = MODEL_STATE.get("current_model")
    plot_dir = os.path.join(PLOT_DIR, model_name)
    os.makedirs(plot_dir, exist_ok=True)
    filepath = os.path.join(plot_dir, filename)
    plt.savefig(filepath, bbox_inches="tight")
    plt.close()
    return f"/{filepath}"  # для HTML


def compute_cell_geometry(COORD: np.ndarray, ZCORN: np.ndarray, nx: int, ny: int, nz: int):
    """
    Вычисляет геометрию ячеек на основе COORD (6 чисел на узел) и ZCORN.

    Parameters
    ----------
    COORD : np.ndarray
        1D массив координат узлов, размер (nx+1)*(ny+1)*6
        Каждое 6-значное значение: [X1,Y1,Z1,X2,Y2,Z2], берем первые XY.
    ZCORN : np.ndarray
        1D массив Z-координат углов ячеек, размер nx*ny*nz*8
    nx, ny, nz : int
        Размеры сетки

    Returns
    -------
    volumes, dx, dy, dz : np.ndarray
        Объемы ячеек, размеры по X, Y и толщина по Z, формы (nz, ny, nx)
    """

    volumes = np.zeros((nz, ny, nx))
    dx = np.zeros((nz, ny, nx))
    dy = np.zeros((nz, ny, nx))
    dz = np.zeros((nz, ny, nx))

    # reshape COORD: (n_nodes, 6)
    n_nodes = COORD.size // 6
    nodes = COORD.reshape((n_nodes, 6))
    x_nodes = nodes[:, 0]
    y_nodes = nodes[:, 1]

    # создаем сетку X, Y
    X = x_nodes.reshape((ny+1, nx+1))
    Y = y_nodes.reshape((ny+1, nx+1))

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                # индекс ZCORN для ячейки
                cell_index = (k * ny * nx + j * nx + i) * 8
                z_corners = ZCORN[cell_index:cell_index+8]

                # координаты XY углов ячейки
                x0, x1 = X[j, i], X[j+1, i+1]
                y0, y1 = Y[j, i], Y[j+1, i+1]

                # 8 углов ячейки
                corners = np.array([
                    [x0, y0, z_corners[0]],
                    [x1, y0, z_corners[1]],
                    [x0, y1, z_corners[2]],
                    [x1, y1, z_corners[3]],
                    [x0, y0, z_corners[4]],
                    [x1, y0, z_corners[5]],
                    [x0, y1, z_corners[6]],
                    [x1, y1, z_corners[7]],
                ])

                # объем через ConvexHull
                try:
                    hull = ConvexHull(corners)
                    volumes[k, j, i] = hull.volume
                except Exception as e:
                    warnings.warn(f"Ошибка ConvexHull для ячейки ({i},{j},{k}): {e}")
                    volumes[k, j, i] = 0.0

                dx[k, j, i] = x1 - x0
                dy[k, j, i] = y1 - y0
                dz[k, j, i] = z_corners.max() - z_corners.min()

    return volumes