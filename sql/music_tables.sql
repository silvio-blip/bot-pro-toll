-- =====================================================
-- TABELAS PARA SISTEMA DE MÚSICA DO BOT DISCORD
-- Execute este SQL no seu Supabase
-- =====================================================

-- Tabela de configurações de música por servidor
CREATE TABLE IF NOT EXISTS music_config (
    id SERIAL PRIMARY KEY,
    server_guild_id BIGINT NOT NULL UNIQUE,
    channel_text_id BIGINT,           -- Canal de texto autorizado para comandos
    channel_voice_id BIGINT,          -- Canal de voz autorizado (opcional)
    role_id BIGINT,                   -- Cargo autorizado para usar comandos
    volume_default INT DEFAULT 50,    -- Volume padrão (0-100)
    max_songs_queue INT DEFAULT 50,   -- Máximo de músicas na fila
    auto_disconnect_minutes INT DEFAULT 30, -- Timeout de inatividade
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de sessão de música (controlador atual)
CREATE TABLE IF NOT EXISTS music_session (
    id SERIAL PRIMARY KEY,
    server_guild_id BIGINT NOT NULL,
    channel_voice_id BIGINT,
    current_controller_id BIGINT,
    current_controller_name VARCHAR(100),
    is_playing BOOLEAN DEFAULT FALSE,
    current_song_title VARCHAR(500),
    current_song_url VARCHAR(1000),
    current_song_duration INT,
    current_position INT DEFAULT 0,
    volume INT DEFAULT 50,
    last_activity TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de fila de músicas
CREATE TABLE IF NOT EXISTS music_queue (
    id SERIAL PRIMARY KEY,
    server_guild_id BIGINT NOT NULL,
    position INT NOT NULL,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    duration INT,
    thumbnail_url VARCHAR(1000),
    added_by_id BIGINT,
    added_by_name VARCHAR(100),
    added_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- ÍNDICES PARA PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_music_config_server ON music_config(server_guild_id);
CREATE INDEX IF NOT EXISTS idx_music_session_server ON music_session(server_guild_id);
CREATE INDEX IF NOT EXISTS idx_music_queue_server ON music_queue(server_guild_id);
CREATE INDEX IF NOT EXISTS idx_music_queue_position ON music_queue(server_guild_id, position);

-- =====================================================
-- ROW LEVEL SECURITY (OPCIONAL)
-- =====================================================

-- Se quiser que todos possam ler mas apenas admins modifiquem:
ALTER TABLE music_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE music_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE music_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "允许所有人读取音乐配置" ON music_config FOR SELECT USING (true);
CREATE POLICY "允许所有人读取音乐会话" ON music_session FOR SELECT USING (true);
CREATE POLICY "允许所有人读取音乐队列" ON music_queue FOR SELECT USING (true);
CREATE POLICY "允许服务角色更新音乐配置" ON music_config FOR ALL USING (true);
CREATE POLICY "允许服务角色更新音乐会话" ON music_session FOR ALL USING (true);
CREATE POLICY "允许服务角色更新音乐队列" ON music_queue FOR ALL USING (true);