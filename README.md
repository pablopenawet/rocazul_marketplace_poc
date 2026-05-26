# rocazul-marketplace-poc

Marketplace POC para plugins de [Claude Code](https://docs.claude.com/en/docs/claude-code/overview).

## Estructura

```
.
├── .claude-plugin/
│   └── marketplace.json   # Manifest del marketplace
└── plugins/               # Cada subdirectorio aquí es un plugin
```

## Instalación

Desde Claude Code:

```
/plugin marketplace add pablopenawet/rocazul_marketplace_poc
```

Luego instala plugins con:

```
/plugin install <nombre-del-plugin>@rocazul-marketplace-poc
```

## Plugins

| Plugin | Versión | Descripción |
|---|---|---|
| [rocazul-bash-guard](plugins/rocazul-bash-guard) | 0.1.0 | Guardián de Bash en dos etapas (`PreToolUse`): chequeo estático rápido (allow/ask/uncertain) + fallback LLM (Haiku 4.5) para casos inciertos. Auto-permite comandos acotados al proyecto, pregunta ante cualquier cosa arriesgada. Fork de [`jvillar/claude-plugins/bash-guard`](https://github.com/jvillar/claude-plugins/tree/main/plugins/bash-guard). |
| [rocazul-security-shield](plugins/rocazul-security-shield) | 0.1.0 | Hook PreToolUse que avisa de patrones inseguros (XSS, injection, eval, pickle, GitHub Actions injection…) en cada Edit/Write/MultiEdit. Fork de [`dev-forge/forge-security`](https://github.com/dmedina-dev/dev-forge/tree/main/plugins/forge-security), que a su vez deriva de [`anthropics/claude-code/security-guidance`](https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance). |
| [rocazul-on-this-day](plugins/rocazul-on-this-day) | 0.2.1 | Hook SessionStart que inyecta un saludo aleatorio con personalidad + una efeméride del día actual (API de Wikipedia "On This Day" con fallback offline en español) para que Claude abra la conversación con tono jocoso. |

## Mantenimiento upstream

Los plugins forquéados de upstreams externos (`rocazul-bash-guard`, `rocazul-security-shield`) se sincronizan con sus orígenes usando el comando `/update-check`, project-scoped.

### Uso

Abre una sesión de Claude Code **dentro del directorio de este marketplace**:

```bash
cd ~/.claude/plugins/marketplaces/rocazul-marketplace-poc
claude
```

Luego invoca:

```
/update-check
```

El comando hace 4 pasos: escanea los plugins externos (los que tienen `.claude-plugin/customizations.json`), consulta sus upstreams vía `gh api` (o `git ls-remote` como fallback), cruza los cambios contra tus customizaciones locales para anticipar conflictos, y opcionalmente aplica los updates preservando lo personalizado.

### Cómo funciona el patrón

- **`customizations.json`** en cada plugin externo (`.claude-plugin/customizations.json`): registra origin (repo, ref, commit SHA), upstream_status, y la lista de tus customizaciones locales con tipo (`removed`, `modified`, `excluded`, `added`, `renamed`).
- **`.upstream/`** en la raíz del marketplace (gitignored): clones git persistentes de los upstreams, uno por repo. Habilita diff preciso entre commits.
- **`docs/customizations-pattern.md`**: schema completo y extensiones rocazul (`type: renamed`, `ancestry[]`).
- **`docs/update-check-guide.md`**: procedimiento detallado que el slash command referencia.

### Visibilidad

`/update-check` sólo aparece en la sesión cuando `cwd` está dentro de este marketplace. No contamina otras sesiones. El patrón está adaptado de [dev-forge](https://github.com/dmedina-dev/dev-forge) (que lo aloja como plugin distribuido); aquí lo mantenemos local porque rocazul-marketplace-poc es de uso propio.
