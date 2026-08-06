# Checklist de Sequência Segura de Release

- [ ] Revisar o baseline `documentation/operations/production-readiness.baseline.json`.
- [ ] Executar `python tooling/dev.py readiness`.
- [ ] Executar `python tooling/dev.py doctor --host <host>` para o alvo da janela.
- [ ] Confirmar que o gate de identidade usa IdP real e nao o IdP efemero de evidência.
- [ ] Confirmar que os segredos criticos nao estao em `__REQUIRED__`, vazios ou placeholders.
- [ ] Registrar blockers ainda abertos de dados, mypy e `npm audit` com aceite formal ou bloqueio de release.
- [ ] Revisar os arquivos que de fato entram na release.
- [ ] Stage apenas dos arquivos aprovados.
- [ ] Criar commit somente apos todos os gates criticos estarem verdes ou aceitos formalmente.
- [ ] Publicar branch/evidencias para revisao remota.
- [ ] Executar rollout da wave 1.
- [ ] Validar health checks e rollback da wave 1 antes da wave 2.
- [ ] Executar rollout da wave 2.
- [ ] Consolidar o pacote final de evidencias e decisao de aprovacao ou rollback.
