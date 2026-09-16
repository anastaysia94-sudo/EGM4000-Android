-- EGM4000 Supabase advisor hardening, 2026-09-16.
-- Mirrors behavior-preserving changes already applied to the shared live project.

-- Evaluate auth.uid() once per statement instead of once per candidate row.
alter policy egm_profiles_insert_self on public.egm_profiles
  with check (id = (select auth.uid()));

alter policy egm_threads_insert_self on public.egm_forum_threads
  with check (
    user_id = (select auth.uid())
    and status = 'published'::text
    and pinned = false
    and synthetic = false
  );

-- The legacy public mirror tables are intentionally client-inaccessible. The active
-- EGM content lives in the egm4000 schema. Make the previous implicit RLS deny
-- explicit without granting new access.
drop policy if exists egm_blog_posts_client_deny_all on public.egm_blog_posts;
create policy egm_blog_posts_client_deny_all on public.egm_blog_posts
  as restrictive for all to anon, authenticated using (false) with check (false);

drop policy if exists egm_survey_feedback_client_deny_all on public.egm_survey_feedback;
create policy egm_survey_feedback_client_deny_all on public.egm_survey_feedback
  as restrictive for all to anon, authenticated using (false) with check (false);

-- Cover foreign keys reported by the Supabase advisor.
create index if not exists audit_events_actor_user_id_idx on egm4000.audit_events(actor_user_id);
create index if not exists blog_comments_post_id_idx on egm4000.blog_comments(post_id);
create index if not exists blog_comments_user_id_idx on egm4000.blog_comments(user_id);
create index if not exists blog_posts_user_id_idx on egm4000.blog_posts(user_id);
create index if not exists forum_replies_thread_id_idx on egm4000.forum_replies(thread_id);
create index if not exists forum_replies_user_id_idx on egm4000.forum_replies(user_id);
create index if not exists forum_threads_user_id_idx on egm4000.forum_threads(user_id);
create index if not exists gameplay_sessions_user_id_idx on egm4000.gameplay_sessions(user_id);
create index if not exists reports_reporter_user_id_idx on egm4000.reports(reporter_user_id);
create index if not exists survey_answers_question_id_idx on egm4000.survey_answers(question_id);
create index if not exists survey_answers_response_id_idx on egm4000.survey_answers(response_id);
create index if not exists survey_questions_survey_id_idx on egm4000.survey_questions(survey_id);
create index if not exists survey_responses_survey_id_idx on egm4000.survey_responses(survey_id);
create index if not exists survey_responses_user_id_idx on egm4000.survey_responses(user_id);
create index if not exists tips_session_id_idx on egm4000.tips(session_id);
create index if not exists tips_user_id_idx on egm4000.tips(user_id);
create index if not exists tokens_user_id_idx on egm4000.tokens(user_id);
create index if not exists egm_blog_posts_user_id_idx on public.egm_blog_posts(user_id);
create index if not exists egm_forum_threads_user_id_idx on public.egm_forum_threads(user_id);
create index if not exists egm_survey_feedback_survey_id_idx on public.egm_survey_feedback(survey_id);
create index if not exists egm_survey_questions_survey_id_idx on public.egm_survey_questions(survey_id);
