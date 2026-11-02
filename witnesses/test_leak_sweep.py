"""Two-sided tests for the leak sweep: each rule catches its leak, and clean text passes.
Leak samples are assembled from fragments so this file does not trip the sweep itself."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leak_sweep as ls

J = "".join


def run(files, private=None):
    with tempfile.TemporaryDirectory() as d:
        for name, text in files.items():
            p = os.path.join(d, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(text)
        pf = None
        if private:
            pf = os.path.join(d, "..", "private-%d.txt" % os.getpid())
            open(pf, "w").write("\n".join(private))
        try:
            return ls.sweep(d, pf)
        finally:
            if pf and os.path.exists(pf):
                os.remove(pf)


def rules(r):
    return sorted({h["rule"] for h in r["hits"]})


def test_clean_text_passes():
    r = run({"a.md": "Ode to Joy is woven by a Jacquard loom. 4/4 at 116 BPM.\n", "b.py": "x = 1\nprint(x)\n"})
    assert r["clean"] and r["files_scanned"] == 2


def test_api_key_shapes():
    assert "key-api" in rules(run({"k.txt": J(["AI", "za", "A" * 35])}))
    assert "key-api" in rules(run({"k.txt": J(["g", "hp_", "a" * 36])}))
    assert "key-private" in rules(run({"k.txt": J(["-----BEGIN ", "RSA PRIVATE", " KEY-----"])}))


def test_private_links():
    assert "private-link" in rules(run({"l.md": J(["https://clau", "de", ".ai/", "artifact/abc"])}))
    assert "private-link" in rules(run({"l.md": J(["gs", "://bucket/obj"])}))


def test_vendor_names():
    assert "vendor-name" in rules(run({"v.md": J(["made with Gem", "ini"])}))
    assert "vendor-name" in rules(run({"v.md": J(["a Clau", "de session"])}))
    assert "vendor-name" not in rules(run({"v.md": "The Opus codec in an Ogg container."}))


def test_cost_only_in_prose():
    assert "cost" in rules(run({"c.md": "It cost $0.27 per call."}))
    assert "cost" not in rules(run({"s.sh": "echo $1 and ${2}"}))
    assert "cost" not in rules(run({"s.py": "price = '$5'"}))


def test_allow_marker():
    assert run({"m.md": J(["Gem", "ini sweep:allow"])})["clean"]
    assert run({"m.md": J(["Gem", "ini sweep:allow vendor-name"])})["clean"]
    assert not run({"m.md": J(["Gem", "ini sweep:allow cost"])})["clean"]


def test_private_strings():
    r = run({"p.md": "project my-secret-project-123 here"}, private=["MY-SECRET-PROJECT-123"])
    assert rules(r) == ["private-string"]
    assert "my-secret" not in str(r["hits"]).lower()
    assert run({"p.md": "project other"}, private=["my-secret-project-123"])["clean"]


def test_skips_build_and_git():
    r = run({"build/x.md": J(["Gem", "ini"]), ".git/y.md": J(["Gem", "ini"]), "ok.md": "fine"})
    assert r["clean"] and r["files_scanned"] == 1


def test_graphics_words_are_not_vendor_names():
    # "vertex" is a GPU term (vertex shader, per-vertex attribute); only the cloud product name is a leak
    assert run({"s.md": "A vertex shader reads per-vertex attributes; ShaderPart type VERTEX.\n"})["clean"]
    assert "vendor-name" in rules(run({"s.md": J(["Ver", "tex ", "AI", " endpoint"])}))
