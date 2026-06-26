"""Interactive chatbot in the terminal.

Run:  python -m app.chat.cli
Then type questions like:
  what AI grants are open?
  fellowships for PhD students
  funding above 10 lakh
  opportunities in Germany
Type 'quit' to exit.
"""
from __future__ import annotations

from app.config import settings
from app.db.database import SessionLocal, init_db
from app.chat.bot import answer


def main():
    init_db()
    db = SessionLocal()
    print("FundRadar chatbot.  Provider:", settings.llm_provider,
          "(set LLM_PROVIDER=gemini in .env for natural-language answers)")
    print("Ask about funding opportunities. Type 'quit' to exit.\n")
    try:
        while True:
            try:
                q = input("you > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q:
                continue
            if q.lower() in {"quit", "exit", "q"}:
                break
            print("\nbot > " + answer(q, db) + "\n")
    finally:
        db.close()
    print("bye")


if __name__ == "__main__":
    main()
