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

## Estado

Marketplace vacío. Aún no se ha publicado ningún plugin.
