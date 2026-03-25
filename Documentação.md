# 📚 Documentação do Bot Discord

## 📋 Índice
1. [Visão Geral](#1-visão-gerais)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Primeiro Passo: Registro](#3-primeiro-passo-registro)
4. [Painel de Controle](#4-painel-de-controle)
5. [Comandos](#5-comandos)
6. [Sistemas Automáticos](#6-sistemas-automáticos)
7. [Loja e Gamificação](#7-loja-e-gamificação)
8. [IA e Downloads](#8-ia-e-downloads)

---

## 1. Visão Geral

Este é um bot Discord completo com as seguintes funcionalidades:

| Categoria | Funcionalidades |
|-----------|----------------|
| **Moderação** | Warns, filtros, logs, anti-raid, captcha, lock |
| **Gamificação** | XP, níveis, ranks, daily, transferências |
| **Loja** | Compra de itens com XP, inventário |
| **IA** | Agente conversacional com múltiplos provedores |
| **Downloads** | Download de áudio (TikTok, YouTube, Instagram) |
| **Social** | Enquetes, dados, eventos |
| **Utilidades** | Remover fundo, ping, crescimento |

---

## 2. Pré-requisitos

### Variáveis de Ambiente Necessárias
O bot requer as seguintes variáveis de ambiente:

```
DISCORD_TOKEN=seu_token_do_bot
SUPABASE_URL=sua_url_do_supabase
SUPABASE_KEY=sua_chave_do_supabase
```

### Permissões do Bot
O bot precisa das seguintes permissões do Discord:
- `Gerenciar Mensagens`
- `Gerenciar Canais`
- `Gerenciar Cargos`
- `Expulsar Membros`
- `Banir Membros`
- `Enviar Mensagens`
- `Ver Mensagens`
- `Anexar Arquivos`
- **Intents**: Members, Message Content, Guilds

---

## 3. Primeiro Passo: Registro

### 3.1 Registrar Servidor

Antes de usar qualquer comando, o administrador deve registrar o servidor:

```
/registrar
```

**O que acontece:**
1. O bot solicita um e-mail para vinculação
2. Envia um código de verificação por e-mail
3. O admin deve verificar com `/verificar`

### 3.2 Alterar Senha (Opcional)

```
/mudar-senha
```

Permite alterar a senha de administrador do servidor.

---

## 4. Painel de Controle

O **Painel de Controle** (`/painel`) é o sistema central de configuração. Todos os sistemas podem ser configurados aqui.

### 4.1 Acessar o Painel

```
/painel
```

> ⚠️ **Requer permissão de administrador**

O painel possui botões organizados por categoria:

| Botão | Categoria |
|-------|-----------|
| 🛡️ Moderação | Configurações de moderação |
| 👑 Administração | Auto-role |
| 📈 Gamificação | XP, níveis, daily |
| 🎉 Social & Diversão | Boas-vindas, eventos |
| 🛒 Loja | Gerenciar itens |
| 🤖 Agente IA | Configurações de IA |

---

### 4.2 🛡️ Moderação

#### Log de Entrada e Saída
| Configuração | Descrição |
|--------------|-----------|
| Canal de Logs | Canal onde as mensagens de entrada/saída serão enviadas |
| Mensagem de Entrada | Mensagem personalizada quando alguém entra (use `{member}`, `{member.mention}`, `{guild}`) |
| Mensagem de Saída | Mensagem personalizada quando alguém sai |
| Imagem de Entrada | URL de imagem opcional para embed de entrada |
| Imagem de Saída | URL de imagem opcional para embed de saída |

**Variáveis disponíveis:**
- `{member}` - Nome do membro
- `{member.mention}` - Menção do membro
- `{member.avatar}` - Avatar do membro
- `{guild}` - Nome do servidor
- `{member_count}` - Total de membros

---

#### Sistema Anti-Raid
| Configuração | Descrição |
|--------------|-----------|
| Ativar | Sim/Não |
| Canal de Alerta | Canal para enviar aviso quando detectar possível raid |
| Número de Entradas | Quantidade de entradas em pouco tempo para considerar raid |
| Janela de Tempo | Tempo em segundos para considerar as entradas |

---

#### Verificação por Captcha
| Configuração | Descrição |
|--------------|-----------|
| Ativar | Sim/Não |
| Canal de Verificação | Canal onde o membro receberá o código |
| Cargo Não Verificado | Cargo dado temporariamente |
| Cargo de Membro | Cargo dado após completar verificação |

**Como funciona:**
1. Membro entra no servidor
2. Recebe o cargo "Não Verificado"
3. Recebe DM com código de 6 caracteres
4. Digita o código no canal de verificação
5. Recebe o cargo de membro

---

#### Sistema de Avisos (Warns)
| Configuração | Descrição |
|--------------|-----------|
| Máximo de Avisos | Quantos warns antes de punir automaticamente |
| Ação Automática | O que fazer ao atingir o limite: Kick ou Ban |

---

#### Filtros

| Filtro | Configurações |
|--------|---------------|
| **Palavras Proibidas** | Lista de palavras separadas por vírgula |
| **Convites** | Ativar/Desativar (bloqueia links do Discord) |
| **Links** | Ativar/Desativar (bloqueia todos os links externos) |
| **CAPS-Lock** | Ativar + Percentual mínimo de letras maiúsculas |
| **Emojis** | Ativar + Quantidade máxima de emojis por mensagem |
| **Spam** | Ativar + Número de mensagens + Intervalo em segundos |

---

### 4.3 👑 Administração

#### Auto-Role (Cargos Automáticos)
| Configuração | Descrição |
|--------------|-----------|
| Ativar | Sim/Não |
| Cargos para Conceder | Lista de cargos dados automaticamente a novos membros |

---

### 4.4 📈 Gamificação

#### Configurações de XP
| Configuração | Descrição | Padrão |
|--------------|-----------|--------|
| Ativar Sistema | Sim/Não | Sim |
| XP Mínimo por Mensagem | XP mínimo ganho por mensagem | 5 |
| XP Máximo por Mensagem | XP máximo ganho por mensagem | 15 |
| Cooldown | Segundos entre cada ganho de XP | 30 |
| XP por Nível | XP necessário para cada nível | 300 |
| Nome dos Pontos | Nome customizado (ex: "moedas", "pontos", "xp") | XP |

---

#### Mensagem de Level Up
| Configuração | Descrição |
|--------------|-----------|
| Mensagem | Texto enviado quando alguém sobe de nível |
| Canal | Canal onde a mensagem será enviada (opcional) |

**Variáveis:**
- `{user}` - Nome do usuário
- `{mention}` - Menção do usuário
- `{level}` - Novo nível
- `{xp}` - XP total

---

#### Recompensa Diária (Daily)
| Configuração | Descrição | Padrão |
|--------------|-----------|--------|
| XP Mínimo | Mínimo ganho no daily | 50 |
| XP Máximo | Máximo ganho no daily | 100 |
| Cooldown | Horas antes de usar novamente | 24 |

---

### 4.5 🎉 Social & Diversão

#### Mensagem de Boas-Vindas
| Configuração | Descrição |
|--------------|-----------|
| Canal | Canal para enviar boas-vindas |
| Mensagem | Texto de boas-vindas |
| Imagem | URL de imagem opcional |

---

#### Eventos
| Configuração | Descrição |
|--------------|-----------|
| Cargo para Criar | Cargo necessário para usar `/criar_evento` |

---

### 4.6 🛒 Loja

#### Gerenciar Itens
| Campo | Descrição |
|-------|-----------|
| Nome | Nome do item |
| Descrição | Descrição do item |
| Preço | Custo em XP |
| Tipo | Tipo do item (ver abaixo) |
| Dados | Dados específicos do tipo |

**Tipos de Itens:**
| Tipo | Descrição | Dados |
|------|-----------|-------|
| `cargo_automatico` | Cargo dado automaticamente | ID do cargo |
| `cargo_colorido` | Cargo com cor específica | ID do cargo |
| `fundo_perfil` | Fundo para cartão de perfil | URL da imagem |
| `avatar_perfil` | Avatar customizado | URL da imagem |

---

### 4.7 🤖 Agente IA

#### Configuração da API
| Configuração | Descrição |
|--------------|-----------|
| URL da API | Endpoint da API do provedor |
| API Key | Chave da API |
| Modelo | Modelo de IA a usar |
| System Prompt | Instruções de comportamento do agente |
| Nome do Agente | Nome exibido nas conversas |

**Provedores Suportados:**
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google AI (Gemini)
- Azure OpenAI
- Ollama (local)
- Groq
- DeepSeek
- E muitos outros...

#### Configurações Adicionais
| Configuração | Descrição |
|--------------|-----------|
| Ativar/Desativar | Habilitar o agente |
| Cargo que pode usar | Cargo necessário para usar IA |
| Cargo que pode ver | Quem pode ver os canais de IA |
| Categoria de Canais | Onde os canais de IA serão criados |

---

## 5. Comandos

### 5.1 Comandos Administrativos

| Comando | Descrição | Uso |
|---------|-----------|-----|
| `/painel` | Abre o painel de controle | Administrador |
| `/sync` | Sincroniza comandos com o Discord | Administrador |
| `/registrar` | Registra o servidor | Administrador |
| `/verificar` | Verifica conta por e-mail | Administrador |
| `/mudar-senha` | Altera senha de admin | Dono do servidor |
| `/embed` | Cria embed personalizado | Administrador |
| `/setup-suporte` | Configura painel de suporte | Administrador |

### 5.2 Moderação

| Comando | Descrição | Parâmetros |
|---------|-----------|-------------|
| `/warn` | Aplica advertência | `membro`, `motivo` |
| `/limpar` | Limpa mensagens | `quantidade`, `usuario` (opcional), `canal` (opcional), `periodo` (opcional) |
| `/lock` | Bloqueia canal | `canal` (opcional), `motivo` (opcional) |
| `/unlock` | Desbloqueia canal | `canal` (opcional) |

### 5.3 Gamificação

| Comando | Descrição |
|---------|-----------|
| `/daily` | Coleta XP diário |
| `/perfil` | Ver perfil e nível |
| `/rank` | Ver ranking de XP |
| `/top_atividade` | Ver ranking de mensagens |
| `/transferir-xp` | Transferir XP para outro membro |

### 5.4 Loja

| Comando | Descrição |
|---------|-----------|
| `/loja` | Ver itens disponíveis |
| `/gerenciar_loja` | Gerenciar itens (Admin) |
| `/inventario` | Ver itens comprados |

### 5.5 IA

| Comando | Descrição |
|---------|-----------|
| `/ia` | Iniciar conversa privada com IA |
| `/ia-clear` | Limpar conversa |
| `/chat` | Conversa rápida com IA |

### 5.6 Downloads

| Comando | Descrição | Parâmetros |
|---------|-----------|-------------|
| `/baixar` | Baixa áudio de vídeo | `url` |

**Plataformas suportadas:** TikTok, Instagram, YouTube, Twitter/X, Facebook, Reddit, SoundCloud

### 5.7 Social & Diversão

| Comando | Descrição | Parâmetros |
|---------|-----------|-------------|
| `/enquete` | Cria enquete | `pergunta`, `opcao_1` a `opcao_10` |
| `/dado` | Lança dado | `lados` (opcional, padrão: 6) |
| `/criar_evento` | Cria evento | `titulo`, `subtitulo`, `imagem` |

### 5.8 Utilidades

| Comando | Descrição |
|---------|-----------|
| `/ping` | Ver latência do bot |
| `/crescimento` | Ver gráfico de crescimento |
| `/remover_fundo` | Remove fundo de imagem |

---

## 6. Sistemas Automáticos

### 6.1 Ativos por Mensagem

| Sistema | Descrição |
|---------|-----------|
| **Ganho de XP** | Concede XP por mensagens (configurável) |
| **Filtro de Palavras** | Remove mensagens com palavras proibidas |
| **Filtro de Convites** | Remove convites do Discord |
| **Filtro de Links** | Remove links externos |
| **Filtro de CAPS** | Remove mensagens com excesso de maiúsculas |
| **Filtro de Emojis** | Remove mensagens com excesso de emojis |
| **Anti-Spam** | Remove spam de mensagens repetidas |
| **Auto-Download** | Detecta e baixa URLs automaticamente |

### 6.2 Ativos por Evento

| Sistema | Descrição |
|---------|-----------|
| **Boas-Vindas** | Envia mensagem quando membro entra |
| **Logs de Entrada/Saída** | Registra entradas e saídas |
| **Auto-Role** | Concede cargos automaticamente |
| **Captcha** | Verificação ao entrar |
| **Anti-Raid** | Detecta possível raid |
| **Account Age** | Expulsa contas muito recentes |

---

## 7. Loja e Gamificação

### 7.1 Sistema de Níveis

```
XP necessário por nível = nível × XP_base
```

Exemplo (XP_base = 300):
- Nível 0 → 0 XP
- Nível 1 → 300 XP
- Nível 2 → 600 XP
- Nível 10 → 3000 XP

### 7.2 Transferência de XP

```
/transferir-xp <membro> <quantidade>
```

- Taxa: 5% do valor transferido
- Exemplo: Transferir 100 XP → Custo real: 105 XP

### 7.3 Daily (Recompensa Diária)

- Ganha XP aleatório entre mínimo e máximo configurados
- Cooldown: 24 horas (configurável)
- Contribui para o nível

---

## 8. IA e Downloads

### 8.1 Agente IA

**Como usar:**
1. Use `/ia` para criar um canal privado
2. Converse no canal criado
3. Use `/ia-clear` para limpar o histórico

**Configurações do painel:**
- Provedor de API
- Modelo
- System prompt customizável
- Permissões por cargo

### 8.2 Downloads

**Como usar:**
```
/baixar <URL>
```

- O áudio é enviado via DM
- Formato: MP3
- Se > 25MB, compactado em ZIP
- Cooldown: 30 segundos

---

## 📊 Tabela Resumo de Configurações

| Sistema | Local de Configuração | Necessita Painel? |
|---------|----------------------|-------------------|
| XP por mensagem | Painel → Gamificação | ✅ |
| Level up | Painel → Gamificação | ✅ |
| Daily | Painel → Gamificação | ✅ |
| Auto-role | Painel → Administração | ✅ |
| Captcha | Painel → Moderação | ✅ |
| Anti-Raid | Painel → Moderação | ✅ |
| Warns | Painel → Moderação | ✅ |
| Filtros | Painel → Moderação | ✅ |
| Logs | Painel → Moderação | ✅ |
| Boas-vindas | Painel → Social | ✅ |
| Loja | Painel → Loja | ✅ |
| IA | Painel → Agente IA | ✅ |

---

## 🔧 Solução de Problemas

### Bot não responde
1. Verifique se o bot está online
2. Use `/ping` para verificar latência
3. Verifique se os comandos estão sincronizados: `/sync`

### XP não está sendo dado
1. Verifique se o sistema está ativado no painel
2. Verifique as configurações de XP

### Filtros não funcionam
1. Ative os filtros no painel
2. Configure as palavras/limites desejados

### IA não responde
1. Verifique a API key no painel
2. Verifique se o agente está ativado
3. Teste a conexão com a API

---

## 📝 Notas

- O prefixo do bot é `!` mas todos os comandos são slash commands (`/`)
- O bot requer permissões de administrador para funcionar completamente
- Todas as configurações são salvas no Supabase
- O painel de controle é a forma recomendada de configurar o bot
