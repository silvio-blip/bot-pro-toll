# 📚 Documentação do Bot Discord

---

## O que é este Bot?

Este é um bot completo para Discord com várias funcionalidades:

| Sistema | O que faz |
|---------|-----------|
| 🛡️ **Moderação** | Protege o servidor com filtros, warns e muito mais |
| ⭐ **Gamificação** | Sistema de XP e níveis para engajar membros |
| 🛒 **Loja** | Loja virtual onde membros compram itens com XP |
| 🤖 **IA** | Chat com Inteligência Artificial |
| ⬇️ **Downloads** | Baixa áudio de vídeos (YouTube, TikTok, etc) |
| 🎉 **Diversão** | Enquetes, dados, eventos |
| 📊 **Utilidades** | Remover fundo de imagens, ping, gráficos |
| 🎫 **Suporte** | Sistema de tickets e hub de suporte |
| 📢 **Denúncias** | Sistema de denúncias de usuários |

---

## Primeiro Passo: Como Começar

### 1. Registrar o Servidor

Antes de tudo, o administrador precisa registrar o servidor:

```
/registrar
```

**O que acontece:**
1. O bot pede seu e-mail
2. Envia um código de verificação
3. Você verifica com `/verificar`

**Pronto!** Agora pode usar todos os comandos.

---

## Todos os Comandos

### 🔧 Comandos Administrativos

| Comando | Descrição |
|---------|-----------|
| `/painel` | 🟢 **O mais importante!** Abre o painel de configurações |
| `/registrar` | 📝 Registra o servidor no bot |
| `/verificar` | ✅ Confirma sua conta com código do e-mail |
| `/mudar-senha` | 🔐 Altera sua senha de administrador |
| `/desregistrar-servidor` | ❌ Remove todos os dados do servidor |
| `/sync` | 🔄 Sincroniza os comandos com o Discord |
| `/embed` | 💬 Cria mensagens bonitas formatadas |
| `/setup-suporte` | 🎧 Configura o sistema de suporte |
| `/setup-tickets` | 🎫 Cria o painel de tickets |

---

### 🎮 Comandos de Gamificação

| Comando | Descrição |
|---------|-----------|
| `/perfil` | 👤 Mostra seu nível, XP e cartão personalizado |
| `/rank` | 🏆 Mostra o ranking dos membros com mais XP |
| `/rank_geral` | 🌟 Ranking geral de XP do servidor |
| `/top_atividade` | 📊 Mostra quem mais conversa |
| `/daily` | 🎁 Ganha XP diário-grátis |
| `/transferir` | 💸 Envia XP para outro membro |
| `/gerenciar_xp` | 💎 Adiciona ou remove XP de um usuário (admin) |
| `/adicionar_moedas` | ➕ Adiciona XP a um usuário (admin) |
| `/remover_moedas` | ➖ Remove XP de um usuário (admin) |

---

### 🛒 Comandos da Loja

| Comando | Descrição |
|---------|-----------|
| `/loja` | 🛒 Ver os itens disponíveis para comprar |
| `/inventario` | 🎒 Ver o que você já comprou |
| `/gerenciar_loja` | 🏪 Adicionar/editar/remover itens da loja (admin) |

---

### 🎲 Comandos de Diversão

| Comando | Descrição |
|---------|-----------|
| `/dado` | 🎲 Lança um dado (pode escolher quantos lados) |
| `/enquete` | 📋 Cria uma votação com botões |
| `/criar_evento` | 🎪 Cria um evento customizado |

---

### 🛡️ Comandos de Moderação

| Comando | Descrição |
|---------|-----------|
| `/warn` | ⚠️ Advertir um membro |
| `/limpar` | 🧹 Apagar mensagens (com opções de quantidade e usuário) |
| `/lock` | 🔒 Bloquear um canal |
| `/unlock` | 🔓 Desbloquear um canal |
| `/denunciar` | 🚨 Denunciar um usuário |

---

### 🤖 Comandos de IA

| Comando | Descrição |
|---------|-----------|
| `/ia` | 💬 Inicia um chat privado com IA |
| `/ia-clear` | 🗑️ Limpa o histórico de conversa |

---

### ⬇️ Comandos de Download

| Comando | Descrição |
|---------|-----------|
| `/baixar` | 📥 Baixa o áudio de um vídeo |

**Plataformas suportadas:** YouTube, TikTok, Instagram, Twitter/X, Facebook, Reddit, SoundCloud

---

### 📊 Comandos de Utilidades

| Comando | Descrição |
|---------|-----------|
| `/ping` | 📡 Ver se o bot está online e a latência |
| `/crescimento` | 📈 Ver gráfico de crescimento do servidor |

---

### 🎫 Comandos de Suporte

| Comando | Descrição |
|---------|-----------|
| `/fechar-ticket` | 🔒 Fecha o ticket atual |

---

### ❓ Comandos de Ajuda

| Comando | Descrição |
|---------|-----------|
| `/ajuda` | ℹ️ Mostra um painel de ajuda interativo |

---

## O que é o /painel?

O `/painel` é o **sistema central de configurações** do bot. É onde o administrador configura tudo.

> **Como usar:** Digite `/painel` e clique nos botões

---

### Categorias do Painel

O painel tem 6 botões principais:

| Botão | O que configura |
|-------|-----------------|
| 🛡️ **Moderação** | Filtros, warns, captcha, logs |
| 👑 **Administração** | Cargos automáticos |
| 📈 **Gamificação** | XP, níveis, mensagens |
| 🎉 **Social** | Boas-vindas, eventos |
| 🛒 **Loja** | Adicionar/editar itens |
| 🤖 **Agente IA** | Configurar a IA |

---

## Configurações do Painel

### 🛡️ Moderação

#### 1. Log de Entrada e Saída
| Configuração | O que é |
|--------------|----------|
| Canal de Logs | Canal onde as mensagens serão enviadas |
| Mensagem de Entrada | Texto quando alguém entra |
| Mensagem de Saída | Texto quando alguém sai |
| Imagem de Entrada | Imagem opcional no embed |

**Variáveis que você pode usar:**
- `{member}` - Nome do membro
- `{member.mention}` - Menção (@membro)
- `{guild}` - Nome do servidor

---

#### 2. Anti-Raid (Proteção contra raid)
| Configuração | O que é |
|--------------|----------|
| Ativar | Ligar ou desligar |
| Canal de Alerta | Onde o bot avisa sobre possível raid |
| Número de Entradas | Quantas entradas rápidas ativam o alerta |
| Janela de Tempo | Em quantos segundos |

---

#### 3. Captcha (Verificação)
| Configuração | O que é |
|--------------|----------|
| Ativar | Ligar ou desligar |
| Canal de Verificação | Onde o membro recebe o código |
| Cargo Não Verificado | Cargo temporário |
| Cargo de Membro | Cargo após verificar |

**Como funciona:**
1. Pessoa entra → recebe cargo temporário
2. Bot envia código no canal
3. Pessoa digita o código → recebe cargo de membro

---

#### 4. Sistema de Warns (Advertências)
| Configuração | O que é |
|--------------|----------|
| Máximo de Avisos | Quantos warns antes de punir |
| Ação Automática | O que fazer: Kick ou Ban |

---

#### 5. Filtros

| Filtro | O que faz |
|--------|-----------|
| **Palavras Proibidas** | Apaga mensagens com essas palavras |
| **Bloquear Convites** | Não deixa postar links do Discord |
| **Bloquear Links** | Não deixa postar nenhum link |
| **Anti-CAPS** | Remove mensagens em MAIÚSCULAS demais |
| **Anti-Emoji** | Remove mensagens com muitos emojis |
| **Anti-Spam** | Remove spam de mensagens repetidas |

---

### 📈 Gamificação

#### 1. Sistema de XP
| Configuração | O que é | Padrão |
|--------------|----------|--------|
| Ativar | Ligar o sistema | Sim |
| XP Mínimo | XP mínimo por mensagem | 5 |
| XP Máximo | XP máximo por mensagem | 15 |
| Cooldown | Segundos entre ganhar XP | 30 |
| XP por Nível | XP necessário para cada nível | 300 |
| Nome dos Pontos | Nome customizado (XP, moedas, etc) | XP |

---

#### 2. Mensagem de Level Up
| Configuração | O que é |
|--------------|----------|
| Mensagem | Texto quando alguém sobe de nível |
| Canal | Onde enviar a mensagem |

**Variáveis:** `{user}`, `{mention}`, `{level}`, `{xp}`

---

#### 3. Recompensa Diária (Daily)
| Configuração | O que é | Padrão |
|--------------|----------|--------|
| XP Mínimo | Mínimo que pode ganhar | 50 |
| XP Máximo | Máximo que pode ganhar | 100 |
| Cooldown | Horas para usar novamente | 24h |

---

### 🛒 Loja

#### Como adicionar itens:
1. Clique em **"Adicionar Novo Item"**
2. Preencha os campos:

| Campo | O que é |
|-----|--------|
| Nome | Nome do item |
| Descrição | O que o item faz |
| Preço | Custo em XP |
| Tipo | Tipo do item |
| Dados | Informações do item |

#### Tipos de Itens:

| Tipo | O que é | Dados necessários |
|------|---------|-------------------|
| `cargo_automatico` | Dá cargo automaticamente | ID do cargo |
| `cargo_colorido` | Cargo com cor | ID do cargo |
| `fundo_perfil` | Fundo do cartão de perfil | URL da imagem |
| `avatar_perfil` | Avatar customizado | URL da imagem |

---

### 🤖 Agente IA

#### Configuração da API
| Configuração | O que é |
|--------------|----------|
| URL da API | Endereço da IA |
| API Key | Chave de acesso |
| Modelo | Modelo da IA (GPT-4, Claude, etc) |
| System Prompt | Como a IA deve agir |
| Nome do Agente | Nome que aparece no chat |

#### Provedores Suportados:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google AI (Gemini)
- Azure OpenAI
- Ollama (IA local)
- Groq
- DeepSeek
- E outros...

#### Configurações de Permissão
| Configuração | O que é |
|--------------|----------|
| Ativar/Desativar | Ligar ou desligar a IA |
| Cargo que pode usar | Quem pode conversar com IA |
| Categoria de Canais | Onde criar os canais de IA |

---

## Sistemas Automáticos

O bot faz coisas automaticamente, sem precisar de comandos:

### Ativos por Mensagem
| Sistema | O que faz |
|---------|-----------|
| **XP por mensagem** | Ganha XP ao conversar |
| **Filtro de palavras** | Apaga palavras proibidas |
| **Filtro de convites** | Bloqueia convites do Discord |
| **Filtro de links** | Bloqueia todos os links |
| **Anti-CAPS** | Remove mensagens em MAIÚSCULAS |
| **Anti-Emoji** | Remove muitos emojis |
| **Anti-Spam** | Remove spam |

### Ativos por Evento
| Sistema | O que faz |
|---------|-----------|
| **Boas-vindas** | Envia mensagem quando alguém entra |
| **Logs** | Registra entradas e saídas |
| **Auto-role** | Dá cargos automaticamente |
| **Captcha** | Verifica novos membros |
| **Anti-Raid** | Detecta raids |
| **Account Age** | Expulsa contas muito recentes |

---

## Como usar os principais sistemas

### Como funciona o XP?

1. Você ganha XP ao enviar mensagens
2. O XP é aleatório (entre mínimo e máximo configurado)
3. Quando atinge 300 XP (padrão), sobe de nível
4. O XP necessário aumenta a cada nível

```
Nível 1 = 300 XP
Nível 2 = 600 XP
Nível 10 = 3000 XP
```

---

### Como usar a Loja?

1. Ganhe XP conversando ou com `/daily`
2. Use `/loja` para ver os itens
3. Clique no que quer comprar
4. Use `/inventario` para equipar

---

### Como funciona o Daily?

1. Use `/daily` uma vez por dia
2. Ganha XP aleatório (entre mínimo e máximo)
3. Aguarde o cooldown (24h) para usar novamente

---

### Como usar a IA?

1. Use `/ia` para criar um canal privado
2. Converse no canal criado
3. A IA lembra tudo que você conversou
4. Use `/ia-clear` para apagar a conversa

---

### Como baixar áudio?

1. Use `/baixar` + URL do vídeo
2. O bot baixa e converte para MP3
3. Envia o arquivo no seu DM

**Exemplo:**
```
/baixar https://www.youtube.com/watch?v=...
```

---

### Como usar o Sistema de Tickets?

1. Use `/setup-tickets` para criar o painel de tickets
2. Membros clicam no botão para abrir um ticket
3. Use `/fechar-ticket` para fechar quando resolvido

---

### Como usar o Sistema de Denúncias?

1. Use `/denunciar` para denunciar um usuário
2. Selecione o motivo e forneça detalhes
3. A moderação recebe a denúncia

---

## Perguntas Frequentes

**O bot não responde?**
→ Use `/sync` para sincronizar os comandos

**Não consigo configurar?**
→ Você precisa ser administrador e ter registrado com `/registrar`

**O que é o /painel?**
→ É onde o administrador configura tudo. Só admins podem usar.

**Como ganho XP?**
→ Conversando no chat (tem um cooldown) ou usando `/daily`

**Como transferir XP?**
→ Use `/transferir` e mencione o usuário

---

## Resumo Rápido

```
Primeiro uso:
1. /registrar
2. /verificar (código do e-mail)
3. /painel (configurar tudo)

Uso diário:
/perfil  - ver nível e XP
/daily   - ganhar XP grátis
/loja    - comprar itens
/rank    - ver ranking
```

---

## Problemas e Soluções

| Problema | Solução |
|----------|---------|
| Bot offline | Verifique se está rodando |
| Comandos não aparecem | Use `/sync` |
| XP não aumenta | Verifique configurações no `/painel` |
| Filtros não funcionam | Ative no `/painel` → Moderação |
| IA não responde | Configure a API no `/painel` → IA |

---

## Especificações Técnicas

- **Linguagem:** Python
- **Biblioteca:** discord.py
- **Banco de Dados:** Supabase (PostgreSQL)
- **Total de Comandos:** 37
- **Total de Cogs:** 34