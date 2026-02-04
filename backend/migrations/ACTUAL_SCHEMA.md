-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.checkpoint_blobs (
thread_id text NOT NULL,
checkpoint_ns text NOT NULL DEFAULT ''::text,
channel text NOT NULL,
version text NOT NULL,
type text NOT NULL,
blob bytea,
CONSTRAINT checkpoint_blobs_pkey PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
CREATE TABLE public.checkpoint_migrations (
v integer NOT NULL,
CONSTRAINT checkpoint_migrations_pkey PRIMARY KEY (v)
);
CREATE TABLE public.checkpoint_writes (
thread_id text NOT NULL,
checkpoint_ns text NOT NULL DEFAULT ''::text,
checkpoint_id text NOT NULL,
task_id text NOT NULL,
idx integer NOT NULL,
channel text NOT NULL,
type text,
blob bytea NOT NULL,
task_path text NOT NULL DEFAULT ''::text,
CONSTRAINT checkpoint_writes_pkey PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
CREATE TABLE public.checkpoints (
thread_id text NOT NULL,
checkpoint_ns text NOT NULL DEFAULT ''::text,
checkpoint_id text NOT NULL,
parent_checkpoint_id text,
type text,
checkpoint jsonb NOT NULL,
metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
CONSTRAINT checkpoints_pkey PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE public.document_chunks (
id uuid NOT NULL DEFAULT uuid_generate_v4(),
document_id uuid NOT NULL,
user_id text NOT NULL,
parent_chunk_id uuid,
chunk_index integer NOT NULL CHECK (chunk_index >= 0),
content text NOT NULL CHECK (length(content) >= 1),
metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
embedding USER-DEFINED,
chunk_type text NOT NULL DEFAULT 'parent'::text CHECK (chunk_type = ANY (ARRAY['parent'::text, 'child'::text])),
created_at timestamp with time zone NOT NULL DEFAULT now(),
updated_at timestamp with time zone NOT NULL DEFAULT now(),
search_vector tsvector,
CONSTRAINT document_chunks_pkey PRIMARY KEY (id),
CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
CONSTRAINT document_chunks_parent_chunk_id_fkey FOREIGN KEY (parent_chunk_id) REFERENCES public.document_chunks(id),
CONSTRAINT document_chunks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.documents (
id uuid NOT NULL DEFAULT uuid_generate_v4(),
source_id uuid,
user_id text NOT NULL,
title text NOT NULL CHECK (length(title) >= 1 AND length(title) <= 500),
blob_path text,
content_hash text,
status text NOT NULL DEFAULT 'pending'::text CHECK (status = ANY (ARRAY['pending'::text, 'processing'::text, 'completed'::text, 'failed'::text])),
created_at timestamp with time zone NOT NULL DEFAULT now(),
updated_at timestamp with time zone NOT NULL DEFAULT now(),
file_type text NOT NULL DEFAULT 'unknown'::text,
file_size integer NOT NULL DEFAULT 0,
chunk_count integer NOT NULL DEFAULT 0,
metadata jsonb DEFAULT '{}'::jsonb,
CONSTRAINT documents_pkey PRIMARY KEY (id),
CONSTRAINT documents_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id),
CONSTRAINT documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.sources (
id uuid NOT NULL DEFAULT uuid_generate_v4(),
user_id text NOT NULL,
name text NOT NULL CHECK (length(name) >= 1 AND length(name) <= 255),
description text,
created_at timestamp with time zone NOT NULL DEFAULT now(),
updated_at timestamp with time zone NOT NULL DEFAULT now(),
CONSTRAINT sources_pkey PRIMARY KEY (id),
CONSTRAINT sources_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.users (
id text NOT NULL,
email text NOT NULL UNIQUE,
credits_used integer NOT NULL DEFAULT 0,
storage_bytes_used bigint NOT NULL DEFAULT 0,
documents_count integer NOT NULL DEFAULT 0,
last_quota_reset timestamp with time zone NOT NULL DEFAULT now(),
created_at timestamp with time zone NOT NULL DEFAULT now(),
updated_at timestamp with time zone NOT NULL DEFAULT now(),
full_name text,
CONSTRAINT users_pkey PRIMARY KEY (id)
);
