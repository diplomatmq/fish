-- Скрипт для добавления индексов производительности в PostgreSQL
-- Запустите этот скрипт для улучшения производительности запросов

-- Индексы для caught_fish (основная таблица с рыбой)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cf_user_sold ON caught_fish(user_id, sold);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cf_user_sold_name ON caught_fish(user_id, sold, fish_name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cf_caught_at ON caught_fish(caught_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cf_fish_name ON caught_fish(fish_name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cf_user_id ON caught_fish(user_id);

-- Индексы для fish_sales_history (история продаж)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fsh_fish_sold ON fish_sales_history(fish_name, sold_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fsh_sold_at ON fish_sales_history(sold_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fsh_fish_name ON fish_sales_history(fish_name);

-- Индексы для players (игроки)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_players_tickets ON players(tickets DESC) WHERE tickets > 0;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_players_gold_tickets ON players(gold_tickets DESC) WHERE gold_tickets > 0;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_players_user_id ON players(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_players_username ON players(username);

-- Индексы для clan_members (члены кланов)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clan_members_user ON clan_members(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clan_members_clan ON clan_members(clan_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clan_members_role ON clan_members(clan_id, role);

-- Индексы для clans (кланы)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clans_owner ON clans(owner_user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clans_level ON clans(level DESC);

-- Индексы для player_trophies (трофеи игроков)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_trophies_user ON player_trophies(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_trophies_active ON player_trophies(user_id, is_active);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_trophies_created ON player_trophies(created_at DESC);

-- Индексы для user_fish_stats (статистика рыбы пользователей)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ufs_user ON user_fish_stats(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ufs_user_fish ON user_fish_stats(user_id, fish_name);

-- Индексы для daily_fish_market (рыбный рынок)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dfm_market_day ON daily_fish_market(market_day);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dfm_fish_name ON daily_fish_market(fish_name);

-- Индексы для fish (справочник рыб)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fish_rarity ON fish(rarity);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fish_price ON fish(price DESC);

-- Индексы для player_rods (удочки игроков)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_rods_user ON player_rods(user_id);

-- Индексы для player_baits (наживки игроков)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_baits_user ON player_baits(user_id);

-- Индексы для player_nets (сети игроков)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_nets_user ON player_nets(user_id);

-- Индексы для chat_configs (конфигурации чатов)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_configs_chat ON chat_configs(chat_id);

-- Индексы для star_transactions (транзакции звезд)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_star_trans_user ON star_transactions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_star_trans_created ON star_transactions(created_at DESC);

-- Индексы для webapp_clan_profiles (профили кланов в веб-приложении)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wcp_clan ON webapp_clan_profiles(clan_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wcp_access ON webapp_clan_profiles(access_type);

-- Индексы для webapp_clan_requests (заявки в кланы)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wcr_user ON webapp_clan_requests(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wcr_clan ON webapp_clan_requests(clan_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wcr_status ON webapp_clan_requests(status);

-- Анализ таблиц после создания индексов
ANALYZE caught_fish;
ANALYZE fish_sales_history;
ANALYZE players;
ANALYZE clan_members;
ANALYZE clans;
ANALYZE player_trophies;
ANALYZE user_fish_stats;
ANALYZE daily_fish_market;
ANALYZE fish;

-- Вывод информации о созданных индексах
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
