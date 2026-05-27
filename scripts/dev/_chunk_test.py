import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repo_rag.chunker import chunk_text
from repo_rag.config import load_global_config

cfg = load_global_config()
print(f"code_tokens={cfg.chunking.code_chunk_tokens}, prose_tokens={cfg.chunking.prose_chunk_tokens}, overlap={cfg.chunking.overlap_tokens}, batch_size={cfg.embedding.batch_size}")

p = Path(r"C:\Raptor\raptor-forms-profile-api\forms-profile-api\EY.TTT.RAPToR.FormsProfile.Business.Tests\FootnoteRulesServiceTests.cs")
text = p.read_text(encoding="utf-8", errors="replace")
print(f"Text: {len(text)} chars")

t0 = time.time()
chunks = chunk_text(p, p.name, text, cfg.chunking.code_chunk_tokens, cfg.chunking.prose_chunk_tokens, cfg.chunking.overlap_tokens)
print(f"Chunking took {time.time()-t0:.3f}s -> {len(chunks)} chunks")

sizes = [len(c.content) for c in chunks]
print(f"  Largest chunk: {max(sizes)} chars")
print(f"  Smallest chunk: {min(sizes)} chars")
print(f"  Total chunked chars: {sum(sizes)}")
print(f"  Original text chars: {len(text)}")
print()
print("First 5 chunks:")
for i, c in enumerate(chunks[:5]):
    print(f"  [{i}] {len(c.content)} chars, lines {c.start_line}-{c.end_line}")
