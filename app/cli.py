import uvicorn


def api() -> None:
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000)


def worker() -> None:
    from .worker import main

    main()

