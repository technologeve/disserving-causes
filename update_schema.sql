-- Add subject column to profiles (for students)
alter table public.profiles 
add column if not exists subject text;

-- Add subject column to projects
alter table public.projects 
add column if not exists subject text;

-- Update the handle_new_user function to include subject
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name, role, organization, subject)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'role',
    new.raw_user_meta_data->>'organization',
    new.raw_user_meta_data->>'subject'
  );
  return new;
end;
$$ language plpgsql security definer;
