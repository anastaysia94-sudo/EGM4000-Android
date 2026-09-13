"""Canonical C009 return-user registry and honest implementation ledger."""

TITLES = [
    'Today dashboard','One-tap session start','Quick recap','Personalized session tips','Tip history','Tip usefulness rating',
    'Daily insight','Weekly performance story','Personal best tracker','Session comparison','Game-by-game comparison',
    'Target-efficiency board','Weapon/cost efficiency','Denomination comparison','Time-of-session analysis','Fatigue warning',
    'Bankroll guard','Responsible-play pause','Variance explainer','Confidence meter','Evidence drawer','What changed? feed',
    'Goals','Goal progress','Healthy tracking streaks','Learning achievements','Personal missions','Coach inbox',
    'Ask EGM about my data','Explain this metric','Screenshot intake','Video review workspace','Voice session notes','Smart tags',
    'Saved views','Universal search','Cross-device sync','Installable PWA','Offline capture','Notification center',
    'Notification controls','Community feed','Follow topics','Bookmarks and saved tips','Private profile controls',
    'Research sandbox','Experiment journal','Feature discovery','Monthly personal report'
]

# These IDs have a concrete UI, route, persistence behavior, or platform control.
# Everything else stays visibly modelled until its actual behavior is verified.
IMPLEMENTED = {
    1,2,3,4,5,7,8,10,11,17,19,20,21,22,25,29,30,36,37,38,39,40,42,43,44,45,46,47,48,49
}

def sync_return_registry(con):
    for number, title in enumerate(TITLES, 1):
        feature_id=f'R{number:03d}'
        status='implemented' if number in IMPLEMENTED else 'modelled'
        existing=con.execute('SELECT id FROM return_features WHERE id=?',(feature_id,)).fetchone()
        if existing:
            con.execute('UPDATE return_features SET title=?,implementation_status=? WHERE id=?',(title,status,feature_id))
        else:
            con.execute('INSERT INTO return_features(id,title,implementation_status) VALUES(?,?,?)',(feature_id,title,status))
        done=1 if status=='implemented' else 0
        if con.execute('SELECT id FROM checklist WHERE id=?',(feature_id,)).fetchone():
            con.execute('UPDATE checklist SET title=?,done=?,notes=? WHERE id=?',(title,done,'C009 verified implementation ledger',feature_id))
        else:
            con.execute('INSERT INTO checklist(id,title,done,notes) VALUES(?,?,?,?)',(feature_id,title,done,'C009 verified implementation ledger'))
    con.commit()

