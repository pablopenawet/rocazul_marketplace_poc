# External Plugin Customizations Pattern

> Patrón adoptado de [dev-forge](https://github.com/dmedina-dev/dev-forge) (`docs/customizations-pattern.md`). Documenta cómo rocazul-marketplace-poc rastrea sus forks de upstreams externos y aplica actualizaciones sin perder customizaciones locales. Extiende el schema original con dos campos propios: `type: "renamed"` y `ancestry[]`.

## Overview

Cuando incorporamos plugins externos a rocazul-marketplace-poc seguimos un patrón **vendor + customizations**:

1. **Track origin** — registramos de dónde viene el plugin (repo, ref, commit).
2. **Document customizations** — cada cambio aplicado sobre el original.
3. **Detect upstream changes** — detectamos nuevas versiones y resumimos qué cambió.
4. **Merge safely** — reconciliamos updates del upstream con nuestras customizaciones locales.

## Why

Los plugins externos evolucionan de forma independiente. Necesitamos:
- Saber exactamente qué cambiamos y por qué.
- Detectar cuándo el upstream publica nuevas versiones.
- Decidir si actualizar (con resumen de cambios).
- Mergear updates sin perder customizaciones.

## customizations.json schema

Cada plugin externo tiene un `customizations.json` en su directorio `.claude-plugin/`:

```json
{
  "origin": {
    "type": "github",
    "repo": "owner/repo-name",
    "path": "plugins/plugin-name",
    "ref": "main",
    "commit": "abc1234def5678",
    "fetched_at": "2026-05-26",
    "check_url": "https://github.com/owner/repo-name/tree/main/plugins/plugin-name"
  },
  "upstream_status": {
    "last_checked": "2026-05-26",
    "latest_ref": "main",
    "latest_commit": "abc1234def5678",
    "has_updates": false,
    "summary": "",
    "changes": []
  },
  "customizations": [
    {
      "id": "custom-01",
      "type": "renamed",
      "target": ".claude-plugin/plugin.json",
      "summary": "Renombrado de original-name a rocazul-foo",
      "reason": "Branding propio del marketplace rocazul-marketplace-poc."
    },
    {
      "id": "custom-02",
      "type": "modified",
      "target": "scripts/some-script.py",
      "summary": "Reducida la sensibilidad del trigger",
      "reason": "El trigger original era demasiado agresivo."
    },
    {
      "id": "custom-03",
      "type": "excluded",
      "target": "tests/",
      "summary": "Excluida infraestructura de tests del upstream",
      "reason": "Sólo relevante para CI del proyecto upstream, no para nuestro uso."
    }
  ],
  "ancestry": [
    {
      "repo": "anthropics/claude-code",
      "path": "plugins/security-guidance",
      "role": "upstream original"
    },
    {
      "repo": "dmedina-dev/dev-forge",
      "path": "plugins/forge-security",
      "role": "fuente directa de este fork"
    }
  ]
}
```

### Field reference

#### `origin`

| Field | Description |
|-------|-------------|
| `type` | Source type: `github` |
| `repo` | Repository en formato `owner/name` |
| `path` | Path dentro del repo (string vacío si es la raíz) |
| `ref` | Git ref (tag, branch) usado en el fetch |
| `commit` | SHA exacto del commit para reproducibilidad |
| `fetched_at` | Fecha del fetch (YYYY-MM-DD) |
| `check_url` | URL donde comprobar nuevas releases/commits |

#### `upstream_status`

| Field | Description |
|-------|-------------|
| `last_checked` | Fecha del último update check |
| `latest_ref` | Ref más reciente encontrada upstream |
| `latest_commit` | Commit SHA más reciente encontrado upstream |
| `has_updates` | Boolean: ¿hay versiones nuevas? |
| `summary` | Resumen de una línea de los updates disponibles |
| `changes[]` | Lista detallada de cambios upstream desde nuestra versión |

Cada entrada en `changes[]`:

```json
{
  "ref": "v2.0.0",
  "date": "2026-04-15",
  "summary": "Soporte multi-model y fix de timeouts de hook",
  "files_changed": ["hooks/hooks.json", "skills/agents/SKILL.md"],
  "conflicts_with_customizations": ["hooks/hooks.json"]
}
```

#### `customizations[]`

| Field | Description |
|-------|-------------|
| `id` | Identificador único (custom-NN) |
| `type` | `removed` \| `modified` \| `excluded` \| `added` \| `renamed` |
| `target` | Archivo o directorio afectado (relativo a la raíz del plugin) |
| `summary` | Qué se cambió |
| `reason` | Por qué — intención detrás de la customización |

### Customization types

- **`excluded`** — contenido upstream no incluido (tests, CI, configs de otras plataformas).
- **`removed`** — contenido upstream eliminado deliberadamente (skills/features no deseadas).
- **`modified`** — contenido upstream cambiado (ajustes de trigger, tweaks de config).
- **`added`** — contenido nuevo no presente upstream (scripts propios, references adicionales).
- **`renamed`** — *(extensión rocazul)* archivo renombrado respecto al upstream, típicamente `plugin.json` por rebranding. El comando `/update-check` lo trata exactamente igual que `modified` para detección de conflictos.

### `ancestry[]` — extensión rocazul (opcional)

Array opcional que documenta la **cadena histórica de forks** cuando un plugin desciende de varios niveles. No participa en el flujo de `/update-check` (sólo `origin.repo` se consulta), pero sirve de contexto para entender la herencia.

Ejemplo: `rocazul-security-shield` desciende de `dev-forge/forge-security`, que a su vez deriva de `anthropics/claude-code/security-guidance`. Su `origin.repo` apunta a dev-forge (el fork directo del que actualiza), y `ancestry[]` documenta el linaje completo.

Cada entrada:

| Field | Description |
|-------|-------------|
| `repo` | Repositorio en formato `owner/name` |
| `path` | Path dentro del repo (string vacío si es la raíz) |
| `role` | Texto libre describiendo el papel (ej: `"upstream original"`, `"fuente directa de este fork"`) |

### Documentar exclusiones explícitamente

Cuando se curan plugins de upstreams grandes con múltiples skills, listar **cada skill excluida** como su propia entry con razón concreta — solapamiento con otro plugin rocazul, narrow-scope, dependencias innecesarias, etc. Esto hace tractable la revisión en segunda pasada: "¿por qué no nos quedamos con X?" tiene respuesta escrita en vez de re-debate.

## Update check flow

### Quick check: "¿Hay updates?"

```
rocazul-bash-guard: ⚡ 1 release ahead (jvillar/claude-plugins @ main)
  "3 commits desde el último fetch"
  ⚠ 1 conflicto con tus customizations (scripts/bash-guard.py)
```

### Detailed check: "¿Qué cambió?"

```
abc1234 (2026-06-10): Ampliada lista SAFE_COMMANDS
  Files: scripts/bash-guard.py
  ⚠ scripts/bash-guard.py — modificaste localmente (custom-03)
def5678 (2026-06-12): Bump del modelo de Haiku 4.5 → 5
  Files: scripts/bash-guard-llm.py
  ✓ Sin conflictos con tus customizations
```

### Update decision: "Aplicar update"

Usa clones persistentes en `.upstream/` (gitignored, una clone por upstream repo).

1. Asegurar `.upstream/{repo-slug}/` (clone si primera vez, fetch si ya cacheado).
2. Checkout del ref objetivo, diff preciso vía `git diff {old}..{new}`.
3. Cross-reference de archivos cambiados contra `customizations[]`.
4. Para cambios limpios (sin match con customization): copiar de `.upstream/` a local.
5. Para conflictos (upstream cambió un fichero `modified` o `renamed`): mostrar diff upstream + versión local + intent de la customization para resolución manual.
6. Actualizar `origin.ref`, `origin.commit`, `origin.fetched_at`.
7. Actualizar `upstream_status`.

## Native plugins

Plugins creados in-house en rocazul (ej: `rocazul-on-this-day`) NO necesitan `customizations.json` — son la fuente original de verdad. Sólo los forks externos lo requieren.
