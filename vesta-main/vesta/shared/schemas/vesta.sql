CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;
COMMENT ON EXTENSION citext IS 'data type for case-insensitive character strings';

CREATE SCHEMA IF NOT EXISTS user;
CREATE SCHEMA IF NOT EXISTS guild;
CREATE SCHEMA IF NOT EXISTS timer;

CREATE TABLE IF NOT EXISTS user.settings (
    user_id BIGINT PRIMARY KEY NOT NULL,
    config JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS guild.settings (
    guild_id BIGINT PRIMARY KEY NOT NULL,
    config JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS reaction_trigger (
    guild_id bigint NOT NULL,
    trigger public.citext NOT NULL,
    emoji text NOT NULL
);

CREATE TABLE IF NOT EXISTS response_trigger (
    guild_id bigint NOT NULL,
    trigger public.citext NOT NULL,
    template text NOT NULL,
    strict boolean DEFAULT false NOT NULL,
    reply boolean DEFAULT false NOT NULL,
    delete boolean DEFAULT false NOT NULL,
    delete_after integer DEFAULT 0 NOT NULL,
    role_id bigint,
    sticker_id bigint
);

CREATE TABLE IF NOT EXISTS counter (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    option text NOT NULL,
    last_update timestamp with time zone DEFAULT now() NOT NULL,
    rate_limited_until timestamp with time zone
);

CREATE TABLE IF NOT EXISTS auto_role (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    action text NOT NULL,
    delay integer
);

CREATE TABLE IF NOT EXISTS logging (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    events TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    webhook_id BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS timer.message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    "interval" integer NOT NULL,
    next_trigger timestamp with time zone NOT NULL
);

CREATE TABLE IF NOT EXISTS timer.purge (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    "interval" integer NOT NULL,
    next_trigger timestamp with time zone NOT NULL,
    method text DEFAULT 'bulk'::text NOT NULL
);

CREATE TABLE IF NOT EXISTS webhook (
    identifier text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    author_id bigint NOT NULL,
    webhook_id bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS starboard (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    self_star boolean DEFAULT true NOT NULL,
    threshold integer DEFAULT 3 NOT NULL,
    emoji text DEFAULT '⭐'::text NOT NULL,
    color integer
);

CREATE TABLE IF NOT EXISTS starboard_entry (
    guild_id bigint NOT NULL,
    star_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    emoji text NOT NULL
);

CREATE TABLE IF NOT EXISTS sticky_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    template text NOT NULL
);

CREATE TABLE IF NOT EXISTS ignored_logging (
    guild_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, target_id)
);

CREATE TABLE IF NOT EXISTS booster_role (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    role_id bigint NOT NULL,
    shared boolean,
    multi_boost_enabled boolean DEFAULT false
);

CREATE TABLE IF NOT EXISTS reaction_role (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    role_id bigint NOT NULL,
    emoji text NOT NULL
);

ALTER TABLE ONLY webhook
    ADD CONSTRAINT webhook_pkey PRIMARY KEY (channel_id, webhook_id);

ALTER TABLE ONLY booster_role
    ADD CONSTRAINT booster_role_pkey PRIMARY KEY (guild_id, user_id);

ALTER TABLE ONLY auto_role
    ADD CONSTRAINT auto_role_pkey PRIMARY KEY (guild_id, role_id, action);

ALTER TABLE ONLY timer.message
    ADD CONSTRAINT message_pkey PRIMARY KEY (guild_id, channel_id);

ALTER TABLE ONLY timer.purge
    ADD CONSTRAINT purge_pkey PRIMARY KEY (guild_id, channel_id);

ALTER TABLE ONLY starboard
    ADD CONSTRAINT starboard_pkey PRIMARY KEY (guild_id, emoji);

ALTER TABLE ONLY starboard_entry
    ADD CONSTRAINT starboard_entry_pkey PRIMARY KEY (guild_id, channel_id, message_id, emoji);

ALTER TABLE ONLY starboard_entry
    ADD CONSTRAINT starboard_entry_guild_id_emoji_fkey FOREIGN KEY (guild_id, emoji) REFERENCES starboard(guild_id, emoji) ON DELETE CASCADE;

ALTER TABLE ONLY sticky_message
    ADD CONSTRAINT sticky_message_pkey PRIMARY KEY (guild_id, channel_id);

ALTER TABLE ONLY response_trigger
    ADD CONSTRAINT response_trigger_pkey PRIMARY KEY (guild_id, trigger);

ALTER TABLE ONLY reaction_trigger
    ADD CONSTRAINT reaction_trigger_pkey PRIMARY KEY (guild_id, trigger, emoji);

ALTER TABLE ONLY counter
    ADD CONSTRAINT counter_pkey PRIMARY KEY (guild_id, channel_id);

ALTER TABLE logging
    ADD COLUMN webhook_id BIGINT,
    ALTER COLUMN events TYPE TEXT[] USING ARRAY[events]::TEXT[],
    ALTER COLUMN events SET DEFAULT ARRAY[]::TEXT[];