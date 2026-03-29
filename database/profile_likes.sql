-- Tabela para sistema de likes no perfil
CREATE TABLE IF NOT EXISTS public.profile_likes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    liked_by BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.profile_likes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all" ON public.profile_likes;
CREATE POLICY "Allow all" ON public.profile_likes FOR ALL USING (true) WITH CHECK (true);

GRANT ALL ON public.profile_likes TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
