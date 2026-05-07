<!-- Obrigado pela contribuição! Preencha as seções abaixo. -->

## Summary

<!-- O que mudou, em 1-3 bullets. -->

## Why

<!-- Contexto / motivação. Link para issue ou ADR se aplicável. -->

## How to test

<!-- Comandos ou passos manuais para verificar a mudança. -->

```bash
ruff check . && ruff format --check .
pytest tests/ -v
```

## Checklist

- [ ] `ruff check .` passa local
- [ ] `ruff format --check .` passa local
- [ ] `pytest tests/` passa local
- [ ] [`CHANGELOG.md`](../CHANGELOG.md) atualizado (se a mudança é visível ao usuário)
- [ ] README / ADR / docstrings atualizados onde fizer sentido
- [ ] Commit messages seguem [Conventional Commits](https://www.conventionalcommits.org/)
