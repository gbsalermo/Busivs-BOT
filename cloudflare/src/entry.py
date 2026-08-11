from workers import Response, WorkerEntrypoint


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url
        method = request.method

        if method == "GET" and url.endswith("/health"):
            return Response.json(
                {
                    "status": "ok",
                    "service": "busivs-bot",
                    "runtime": "cloudflare-worker",
                    "stage": "6.1",
                }
            )

        if method == "POST" and url.endswith("/telegram/webhook"):
            return Response.json(
                {
                    "ok": False,
                    "status": "webhook_not_enabled_yet",
                    "stage": "6.1",
                },
                status=501,
            )

        return Response.json(
            {
                "service": "BUSIVS BOT",
                "status": "cloudflare-adapter-running",
                "health": "/health",
                "webhook": "/telegram/webhook",
            }
        )
