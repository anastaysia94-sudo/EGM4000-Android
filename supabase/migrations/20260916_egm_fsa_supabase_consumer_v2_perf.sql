-- Cover the player_key foreign key on the v2 F.S.A. session-link table.
create index if not exists idx_egm_fsa_session_player_key
  on egm4000.fsa_session_links(player_key);
