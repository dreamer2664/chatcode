# YT01 research dossier — "How Git Actually Remembers Everything"

Verified 2026-10-15 (UTC) by odysseus. Links re-opened, not guessed.

## Primary / authoritative sources
1. **Pro Git (Chacon & Straub), chapter "Git Internals"** — CC BY-NC-SA 3.0,
   free to read: https://progit3.com/ (and git-scm.com/book). Sections:
   object model (blob/tree/commit), SHA-1 addressing, the plumbing commands.
   This is THE canonical primary-adjacent text; diagrams will be original even
   though the facts come from here.
2. **git source code (GPL-2.0-only)** — https://github.com/git/git — for the
   on-screen plumbing demonstration: `hash-object`, `cat-file`, `.git/objects`
   fan-out directory layout. Demo run on a real scratch repo; screen recording
   is original footage of my own machine's actions.
3. **git user manual (project docs)**: https://git-scm.com/docs/user-manual
   — object naming, the object database section.
4. Context/secondary: Git 3.0 / SHA-256 migration notes (used ONLY if a
   10-second "the IDs are getting longer" aside survives the edit); otherwise cut.

## Claim sketch (to be expanded in claims.md with timestamps once scripted)
- "Every version lives exactly once, named by its content's hash" → Pro Git,
  Git Internals §object-storage + hands-on hash-object output.
- "A tree is a directory listing of hashes" → Pro Git ch10 + cat-file -p demo.
- "A commit points to one tree and to its parents" → Pro Git + cat-file -p.
- "Identical content under different paths shares one blob" → Pro Git; verified
  live in the demo (two identical files, one hash).
- "Detached HEAD isn't broken — it's your safety net" → user manual section
  "Detached HEAD" + live recovery demonstration.
