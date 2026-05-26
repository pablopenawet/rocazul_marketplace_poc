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
| [rocazul-security-shield](plugins/rocazul-security-shield) | 0.1.0 | Hook PreToolUse que avisa de patrones inseguros (XSS, injection, eval, pickle, GitHub Actions injection…) en cada Edit/Write/MultiEdit. Fork de [`dev-forge/forge-security`](https://github.com/dmedina-dev/dev-forge/tree/main/plugins/forge-security), que a su vez deriva de [`anthropics/claude-code/security-guidance`](https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance). |
