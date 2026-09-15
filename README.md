# ShyDevs — Quadro de Tarefas

Projeto com backend em **Django + Django REST Framework** e frontend em **Vue 3 (Vite)**.

## Estrutura

- `backend/` — API Django (SQLite, sem necessidade de serviços externos)
- `frontend/` — SPA Vue 3

## Rodando o backend

```bash
cd backend
venv/Scripts/python manage.py runserver 8000
```

O ambiente virtual (`venv/`) e as dependências já estão instalados. O banco está **limpo** (sem tarefas nem pessoas de demonstração) — só existe a conta administradora. Rodar `python manage.py seed` novamente apaga tudo (tarefas, pessoas, histórico, tokens) e recria apenas o admin do zero.

**Login do administrador**: usuário `Akanub`, senha `akanub123` (altere depois pelo admin do Django em `/admin/` ou crie outro fluxo de troca de senha).

### Permissões

- **Apenas o administrador (`Akanub`)** pode criar/editar/excluir tarefas, subtarefas e gerenciar pessoas (adicionar/remover na aba "Equipe").
- Qualquer outra pessoa cadastrada pode fazer login (se tiver senha) só para ver o quadro e usar o filtro "Minhas tarefas" — sem poder alterar nada.
- Visitantes sem login também podem ver tudo (leitura é pública); só a escrita exige ser o admin.

API disponível em `http://127.0.0.1:8000/api/`:
- Autenticação: `POST /api/auth/login/`, `POST /api/auth/logout/`, `GET /api/auth/me/` (token via header `Authorization: Token <key>`)
- `GET/POST /api/tasks/` · `GET/PATCH/DELETE /api/tasks/<id>/` (escrita só admin)
- `GET /api/tasks/roles/` · `GET /api/tasks/balance/` · `GET /api/tasks/dashboard/`
- `POST /api/tasks/bulk_update/` · `DELETE /api/tasks/bulk-delete/` (só admin)
- `GET/POST /api/subtasks/` (filtra por `?task=<id>`) · `PATCH/DELETE /api/subtasks/<id>/` (escrita só admin)
- `GET /api/activities/` (filtra por `?task=<id>`, leitura pública)
- `GET/POST /api/people/` (criar só admin) · `PATCH/DELETE /api/people/<id>/` (só admin) · `POST /api/people/<id>/photo/` (upload de avatar, só admin)
- `GET/POST /api/attachments/` (filtra por `?task=<id>`; criar exige login, qualquer pessoa) · `DELETE /api/attachments/<id>/` (autor do anexo ou admin)
- `GET /api/settings/` (nome do projeto, público) · `PATCH /api/settings/` (só admin)

Admin do Django em `http://127.0.0.1:8000/admin/` (crie um superusuário com `python manage.py createsuperuser` para acessá-lo).

## Rodando o frontend

```bash
cd frontend
npm install
npm run dev
```

Abre em `http://localhost:5173`. As chamadas `/api/*` e `/media/*` são redirecionadas (proxy do Vite) para `http://127.0.0.1:8000`, então rode o backend antes.

## Funcionalidades

- Nome do projeto ("Slayer Reborn") editável pelo admin — clique no chip ao lado do logo
- **Múltiplos administradores**: qualquer admin pode tornar outra pessoa admin (ou tirar) na aba "Equipe" — sempre precisa sobrar pelo menos um
- Login com senha por pessoa; só admins podem alterar tarefas ou gerenciar a equipe
- Aba "Equipe" (admin): adicionar/remover pessoas, com senha opcional para cada uma
- "Minhas tarefas" e upload de foto de perfil (admin)
- Quadro em tabela ou Kanban (drag-and-drop, só admin) por status
- **Página dedicada por tarefa** (`/tasks/:id`, URL própria e compartilhável): detalhes, checklist, histórico e **anexos** (imagens, vídeos ou links) — qualquer pessoa logada pode anexar prova do que fez; edição da tarefa em si continua só admin
- Ações em massa (selecionar várias tarefas → mudar status / excluir) — só admin
- Histórico de atividades (log automático de criação, mudança de status, reatribuição, anexos)
- Dashboard com gráficos de status, prioridade, cargo e carga por pessoa
- Atalhos de teclado: `/` busca, `N` nova tarefa, `Esc` fecha modais
- Animações GSAP em toda a interface (entrada, modais, listas, cards do Kanban, barras do dashboard, toasts, menu de conta), tema escuro, ícones Flaticon, easter egg (clique no mascote)

### Arquitetura do frontend

O app usa **Vue Router** (rotas reais: `/`, `/dashboard`, `/history`, `/team`, `/tasks/:id`) e foi dividido em componentes menores e independentes (`AppHeader`, `BoardPage`, `TaskTable`, `RoleChipsBar`, `CreateTaskModal`, `TaskPage`, `AttachmentsPanel`, etc.), cada um buscando seus próprios dados. Isso corrige o travamento que existia ao abrir o modal de nova tarefa: antes, todo o quadro (com a tabela inteira) vivia num único componente gigante, então qualquer clique forçava o Vue a re-renderizar tudo; agora cada página/modal é isolado e só re-renderiza o que realmente mudou.

## Fora do escopo desta versão (precisa de credenciais/infra sua)

- **Webhook do Discord** para avisos de tarefa atrasada/atribuída — dá pra adicionar rápido assim que você tiver a URL do webhook do seu servidor.
- **E-mail/push de lembrete de prazo** — precisa de um servidor SMTP (ou serviço de push) configurado.
- **Tempo real via WebSockets** (Django Channels) — hoje cada pessoa vê os dados de quando carregou a página; dá pra evoluir para sincronização ao vivo se fizer sentido pro time.
- **Tema claro alternável** — o app está todo em estilos inline no tema escuro; migrar para variáveis CSS é um refactor à parte, posso fazer sob demanda.
