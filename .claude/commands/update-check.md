---
description: Comprueba si los plugins externos del marketplace tienen actualizaciones upstream, muestra cambios y conflictos con tus customizations locales, y opcionalmente aplica los updates.
---

Comprueba todos los plugins externos de rocazul-marketplace-poc en busca de updates upstream y opcionalmente los aplica.

**Step 1 — Scan plugins**
Escanea todos los `plugins/*/.claude-plugin/customizations.json`. Clasifica cada plugin:
- External: tiene `origin.type = "github"` → elegible para update check
- Native: sin `customizations.json` → skip

Ver `docs/update-check-guide.md` § Plugin scanning.

**Step 2 — Check upstreams**
Para cada plugin elegible, comprueba upstream para nuevas versiones usando `gh api` (primario) o `git ls-remote` (fallback). Presenta una tabla resumen:

```
Plugin                       Upstream                     Current      Latest     Status
──────────────────────────── ──────────────────────────── ──────────── ────────── ──────
rocazul-bash-guard           jvillar/claude-plugins       58e27a3      abc1234    ⚡ 3 commits ahead
rocazul-security-shield      dmedina-dev/dev-forge        14f138d      14f138d    ✓ up to date
rocazul-on-this-day          —                            —            —          ⊘ native
```

Ver `docs/update-check-guide.md` § Upstream check y § Quick summary format.

**Step 3 — Detail on request**
Pregunta: "¿Detalle de algún plugin? Escribe el nombre(s), 'all', o Enter para saltar."

Para cada plugin solicitado, muestra releases/commits desde la versión actual y análisis de conflictos contra entries `customizations[]`.

Ver `docs/update-check-guide.md` § Detailed view per plugin.

**Step 4 — Apply on request**
Pregunta: "¿Aplicar updates? Escribe el nombre(s) del plugin, o Enter para saltar."

Para cada plugin a actualizar, ofrece tres opciones:
- **apply** — sync del upstream clone en `.upstream/`, copia cambios, preserva customizations locales
- **reset** — copia fresca desde `.upstream/`, limpia customizations
- **skip** — dejar como está

Usa clones full persistentes en `.upstream/` (gitignored). Primer apply clona, siguientes hacen fetch. Una clone por upstream repo, compartida entre plugins del mismo repo.

Ejecuta la acción elegida y muestra un resumen post-update.

Ver `docs/update-check-guide.md` § Apply update flow.

---

**Importante:** este comando es project-scoped — sólo está visible cuando trabajas con `cwd` dentro de rocazul-marketplace-poc. Para invocarlo, abre tu sesión de Claude Code dentro del directorio del marketplace.
