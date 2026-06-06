# Frozen test inputs (3 — variety across stack: TS frontend / Python backend / cross-cutting auth)

Repo under test: `~/work/DocIQ-Sphere` (turbo monorepo).

T1. (TS/Next.js frontend feature) "Understand how the chat feature works in the web app: the
chat-session orchestration, the timeline/transcript rendering, the message/types model, and where
a question gets sent off to the backend. I need the main implementation files and how they connect."

T2. (Python backend engine) "Understand the docx atomic-processing engine in the
docx-atomic-backend service: the FastAPI entry point, the core engine that turns a .docx into
atomic operations, and the main pipeline stage modules. Where does a request enter and how does it
flow into the engine?"

T3. (cross-cutting auth) "Understand the authentication system end-to-end: the betterAuth
integration on the Convex side, the web app's auth server/client libs, and the Next.js route that
handles auth requests. How do the web app and Convex backend connect for auth?"
