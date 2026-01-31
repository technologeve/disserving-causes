-- Function to handle new user creation
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name, role, organization)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'role',
    new.raw_user_meta_data->>'organization'
  );
  return new;
end;
$$ language plpgsql security definer;

-- Trigger to call the function on new user creation
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- We can now drop the insert policy for profiles as it will be handled by the trigger (which bypasses RLS)
-- But keeping it doesn't hurt. The trigger runs as system so it ignores RLS.
