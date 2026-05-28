import { tool } from "@opencode-ai/plugin"

export default tool({
  description:
    "Управление сервером FastAPI (start/stop/restart/status/logs)",
  args: {
    action: tool.schema
      .enum(["start", "stop", "restart", "status", "logs"])
      .describe("Действие"),
  },
  async execute(args, context) {
    const workdir = context.worktree || context.directory
    const venv = "/home/ed_ubuntu/.virtualenvs/fastApiProject"
    const logFile = "/tmp/fastapi.log"

    switch (args.action) {
      case "start": {
        const check =
          await Bun.$`curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/`
            .text()
        if (check.trim() !== "000") return "Сервер уже запущен"
        await Bun
          .$`source ${venv}/bin/activate && nohup uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ${logFile} 2>&1 &`
          .cwd(workdir)
        await Bun.sleep(2000)
        const status =
          await Bun.$`curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/`
            .text()
        return `Сервер запущен. HTTP ${status.trim()}`
      }
      case "stop": {
        await Bun.$`pkill -f "uvicorn main:app" 2>/dev/null`.cwd(workdir)
        return "Сервер остановлен"
      }
      case "restart": {
        await Bun.$`pkill -f "uvicorn main:app" 2>/dev/null`.cwd(workdir)
        await Bun.sleep(1000)
        return (await execute({ action: "start" }, context)).toString()
      }
      case "status": {
        const code =
          await Bun.$`curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/`
            .text()
        if (code.trim() === "000") return "Сервер не запущен"
        return `Сервер работает (HTTP ${code.trim()})`
      }
      case "logs": {
        const { stdout, stderr, exitCode } =
          await Bun.$`tail -50 ${logFile}`.nothrow()
        const logs = stdout.toString().trim()
        if (exitCode !== 0 || !logs) return "Логов нет"
        return logs
      }
    }
  },
})
