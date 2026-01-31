-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- PROFILES TABLE
-- Extends the auth.users table
create table public.profiles (
  id uuid references auth.users not null primary key,
  email text,
  full_name text,
  role text check (role in ('student', 'charity', 'professor')),
  organization text,
  bio text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS for profiles
alter table public.profiles enable row level security;

-- Policy: Public profiles are viewable by everyone
create policy "Public profiles are viewable by everyone"
  on public.profiles for select
  using ( true );

-- Policy: Users can insert their own profile
create policy "Users can insert their own profile"
  on public.profiles for insert
  with check ( auth.uid() = id );

-- Policy: Users can update their own profile
create policy "Users can update own profile"
  on public.profiles for update
  using ( auth.uid() = id );

-- PROJECTS TABLE
create table public.projects (
  id uuid default uuid_generate_v4() primary key,
  title text not null,
  description text not null,
  requirements text,
  charity_id uuid references public.profiles(id) not null,
  status text default 'open' check (status in ('open', 'closed')),
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS for projects
alter table public.projects enable row level security;

-- Policy: Everyone can view projects
create policy "Projects are viewable by everyone"
  on public.projects for select
  using ( true );

-- Policy: Charities can create projects
create policy "Charities can create projects"
  on public.projects for insert
  with check ( auth.uid() = charity_id );

-- INTERESTS TABLE (Connections)
create table public.interests (
  id uuid default uuid_generate_v4() primary key,
  project_id uuid references public.projects(id) not null,
  user_id uuid references public.profiles(id) not null,
  message text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(project_id, user_id)
);

-- Enable RLS for interests
alter table public.interests enable row level security;

-- Policy: Users can view their own interests, and project owners can view interests on their projects
create policy "Users can view own interests and project owners can view applications"
  on public.interests for select
  using ( 
    auth.uid() = user_id OR 
    auth.uid() in (
      select charity_id from public.projects where id = project_id
    )
  );

-- Policy: Users can create interests (apply)
create policy "Users can create interest"
  on public.interests for insert
  with check ( auth.uid() = user_id );
