// One entry per push to main, newest first. The sprint shown in the hero is the
// first entry's version: add a new entry (and bump the version) with every push.
export const releases = [
  {
    version: '24.11',
    items: [
      'Quem participa de uma tarefa em grupo agora aparece nela em "Minhas tarefas", no filtro por pessoa e na busca, e a tarefa conta nos cargos de todos os participantes.',
    ],
  },
  {
    version: '24.10',
    items: [
      'Checklist de tarefa em grupo: todos fazem o mesmo checklist e cada pessoa marca as suas etapas. Uma etapa só conta como feita quando todos terminam, e dá para ver quem já concluiu cada uma.',
      'Menu ⋮ no checklist para definir quem faz primeiro (ex.: animador, depois scripter, depois VFX). Cada um só marca uma etapa depois de quem vem antes, e o próximo recebe uma DM "Sua vez!" no Discord.',
    ],
  },
  {
    version: '24.9',
    items: [
      'Novo tipo de tarefa: em grupo. Ao atribuir uma tarefa, escolha no topo entre solo ou em grupo, e no grupo selecione várias pessoas ou cargos inteiros.',
      'Todo mundo do grupo pode mudar o status e marcar o checklist, e a tarefa conta na carga de trabalho de cada um.',
      'O Discord marca e manda os lembretes por DM para cada pessoa do grupo.',
    ],
  },
  {
    version: '24.8',
    items: [
      'Tarefas podem depender de outra: fica bloqueada (cadeado "Aguardando SD-xxx") até a outra ser concluída, e a página das duas avisa isso.',
      'Quando a tarefa da qual outra depende é concluída, o responsável recebe uma DM "Tarefa liberada".',
      'O bot não manda mais o lembrete "Ainda não começou?" para quem já tem uma tarefa em andamento, nem para tarefas bloqueadas.',
      'Aba Bot: imagens, vídeos e GIFs que as pessoas mandam para o bot aparecem na conversa, com visualizador.',
    ],
  },
  {
    version: '24.7',
    items: [
      'Noob 3D girando no lugar da logo (topo e cabeçalho da página); clique nele para girar como um fidget spinner.',
      'Quanto mais tarefas em aberto você tem (a partir de 3), mais o noob gira rápido e "glitcha".',
      'Concluir uma tarefa faz o noob dar um giro de comemoração.',
      'Novo "?" ao lado da sprint com o histórico de novidades.',
      'Com todas as etapas do checklist feitas, só dá para salvar a tarefa marcando Concluída e escrevendo a nota de conclusão.',
    ],
  },
  {
    version: '24.6',
    items: [
      'Marcar uma etapa do checklist move a tarefa de Pendente para Em andamento automaticamente.',
      'Corrigido: vídeos das referências voltavam para o começo ao pular na barra de progresso.',
      'Links do YouTube/Vimeo agora abrem no minuto do link (?t=90, 1m30s).',
    ],
  },
  {
    version: '24.5',
    items: [
      'Nova aba Referências nas tarefas, com links e arquivos agrupados e um visualizador de mídia.',
      'Deixado claro o que é anexo (entrega do responsável) e o que é referência (consulta).',
      'Site responsivo para celular.',
      'A descrição da tarefa cresce para caber o texto ao abrir.',
    ],
  },
  {
    version: '24.4',
    items: [
      'Vários projetos, com seletor no cabeçalho.',
      'Notificações no Discord por webhook e lembretes por DM do bot.',
      'Aba Bot com tudo que o bot enviou e recebeu.',
    ],
  },
]

export const currentVersion = releases[0].version
