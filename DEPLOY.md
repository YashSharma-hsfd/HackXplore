# DEPLOY.md — Backend on Hugging Face Spaces (Docker)

Deploys the FastAPI backend (with the loaded corpus + knowledge graph baked in)
to a free HF Space. The build runs **on HF's servers** — nothing builds on your
machine, and it uses **zero local disk**.

> The repo is already deploy-ready: the `Dockerfile` bakes in `chroma_store/` +
> `graph_store/`, and `README.md` carries the HF Space config (`sdk: docker`,
> `app_port: 8000`). You mainly create the Space and set one secret.

---

## 1. One-time: HF account + token
1. Sign up at <https://huggingface.co> (free).
2. Create a **Write** token: <https://huggingface.co/settings/tokens> → *New token*
   → role **Write** → copy it (used as the git password when pushing).

## 2. Create the Space
<https://huggingface.co/new-space> →
- **Owner**: you · **Space name**: e.g. `two-stroke-kb`
- **License**: any (e.g. MIT)
- **Space SDK**: **Docker** → **Blank**
- **Hardware**: **CPU basic** (free, 16 GB RAM — enough for BGE-M3 + reranker)
- **Visibility**: Public
- *Create Space.*

## 3. Push the code to the Space
The Space is its own git repo. From the project folder:
```powershell
cd C:\Users\avish\Desktop\HackXplore
git remote add space https://huggingface.co/spaces/<your-user>/two-stroke-kb
git push space main
```
- When prompted: **username** = your HF username, **password** = the Write token
  from step 1. (Or run `huggingface-cli login` once to cache it.)
- This pushes everything, incl. `chroma_store/` (corpus) and `graph_store/`
  (graph). PDFs go via LFS (HF supports it).

## 4. Set secrets (Space → Settings → *Variables and secrets*)
| Secret | Required? | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ **required** | answer generation (Mistral) + the judge |
| `TAVILY_API_KEY` | optional | enables the 🌐 web-search toggle (else it 503s) |
| `GEMINI_API_KEY` | optional | OCR fallback for scanned PDFs |
| `REDIS_URL` | optional | embedding cache (your Upstash `rediss://` URL); app runs fine without it |

HF injects these as environment variables — the app reads them directly (no
`.env` needed on the Space). **Never** commit real keys.

## 5. Build + verify
- After the push (and on each secret change) the Space **rebuilds** (~5–10 min
  first time). Watch the **Logs** tab.
- **First query is slow** (~2–5 min): the container downloads BGE-M3 +
  `bge-reranker-v2-m3` (~4 GB) on first use, then caches them and is fast.
- Verify (replace with your Space URL, shown at the top of the Space page):
  - `https://<your-user>-two-stroke-kb.hf.space/health` → `{"status":"ok"}`
  - `.../docs` → Swagger
  - `POST /query` `{ "question": "What is the freezing point of Jet A1?" }`

**Tip for the demo:** hit `/health` a few minutes before presenting to warm the
Space (free Spaces sleep when idle and cold-start slowly).

---

## 6. Frontend (later)
Two options once the React app is build-ready:
- **Combine into this image** (one URL, no CORS): add the React source to the
  repo, add a Node build stage to the `Dockerfile` (`npm run build`), and serve
  the `dist/` from FastAPI via `StaticFiles`. Build the React app with
  `VITE_API_URL=""` (same-origin).
- **Separate** (faster to iterate): deploy the React app to **Vercel/Netlify**
  and set `VITE_API_URL` to this Space's URL. CORS is already wildcard, so it
  just works.

Updating the deployed backend later = `git push space main` again.
