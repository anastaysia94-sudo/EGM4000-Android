from __future__ import annotations
from collections import Counter

IMPLEMENTED={1,2,3,5,7,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,29,30,31,32,33,34,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,63,64,68,70,96,97,99,100}
PROVIDER_CONFIG=set(range(71,96))

TITLES=[
'Owner-only access boundary','Secure owner session login','CSRF protection for owner writes','Owner password recovery controls','Owner role authorization','Owner multi-factor authentication','Admin audit event logging','Owner session expiration','Owner active-session revocation','Production secure-cookie mode',
'User account directory','User status visibility','User profile inspection','Synthetic-vs-real account labeling','User search and filters','User account suspension model','Registered-user role visibility','Mobile-token account linkage','Account activity counts','User-generated content ownership trace',
'Open report queue','Report filtering','Thread moderation','Reply moderation','Blog post moderation','Blog comment moderation','Bulk moderation actions','Moderator notes','Content restoration','Report resolution workflow',
'Owner blog publishing','Pending blog review visibility','Community content status control','Pinned thread controls','Category management','Tag management','Homepage content controls','Announcement publishing','Editorial scheduling','Draft preview',
'Survey lifecycle controls','Survey start/end scheduling','Survey frequency caps','Survey response export','Survey analytics dashboard','Survey builder','Survey audience targeting','Survey consent control','Pseudonymous visitor classification','Persistent survey response storage',
'Gameplay-session overview','Tips/coaching overview','Per-user gameplay drilldown','Normalized event metrics','Live-session analysis','Replay evidence inspection','Coaching experiment comparison','Cross-session trend dashboard','Evidence-quality diagnostics','Adapter health visibility',
'F.S.A. bridge status','F.S.A. duplicate-event diagnostics','System health counts','Operational dashboard metrics','Database/storage health','Background-job status','API error dashboard','Audit trail visibility','Backup status','Environment/config readiness',
'Premium subscription plans','Usage-based coaching plan','Advanced analytics subscription','Team/coach workspace plan','Research Lab paid tier','Export/report add-on','Priority processing add-on','Premium community membership','Partner referral tracking','Affiliate attribution',
'Sponsored educational placements','Creator/coach marketplace fee','White-label licensing','API access plan','Enterprise workspace licensing','Advanced retention insights add-on','Custom report package','Premium data retention tier','Founder/admin analytics add-on','Hardware/capture partner referrals',
'Training/course upsells','Optional tip-jar/donation support','Promotional bundle controls','Trial/coupon controls','Billing-provider reconciliation',
'Evidence-label policy enforcement','No-profit-guarantee safety boundary','Retention-feature registry visibility','Canonical checklist/ledger visibility','Owner command-center dashboard'
]

CATEGORIES=[]
for i in range(1,101):
    if i<=10:CATEGORIES.append('Access & Security')
    elif i<=20:CATEGORIES.append('Users & Accounts')
    elif i<=30:CATEGORIES.append('Community Moderation')
    elif i<=40:CATEGORIES.append('Content & Publishing')
    elif i<=50:CATEGORIES.append('Surveys & Research')
    elif i<=60:CATEGORIES.append('Gameplay Intelligence')
    elif i<=70:CATEGORIES.append('Operations & Analytics')
    elif i<=95:CATEGORIES.append('Monetization')
    else:CATEGORIES.append('Governance & Platform')

EVIDENCE={
1:'Server owner-only routes require role=owner.',2:'Owner login uses PBKDF2-backed account authentication.',3:'Owner write endpoints enforce X-CSRF-Token.',5:'need(owner=True) enforces the owner boundary.',7:'audit_events records owner and user actions.',10:'EGM_SECURE_COOKIES enables Secure session cookies.',
11:'GET /api/admin/users exposes the owner account directory.',12:'users.status is persisted and returned by the owner directory.',13:'GET /api/admin/user returns persisted profile fields.',14:'users.is_synthetic explicitly labels seeded accounts.',15:'GET /api/admin/users supports q, status, synthetic and limit filters.',16:'users.status provides suspension/inactivation model.',17:'role is exposed to authenticated owner account views.',18:'mobile_tokens are linked to users.',19:'owner user drilldown and dashboard expose account-linked activity counts.',20:'forum/blog records persist user_id ownership trace.',
21:'GET /api/admin/reports provides an owner-only report queue.',22:'GET /api/admin/reports filters by status and target_type.',23:'POST /api/admin/moderate supports owner hide/restore/publish/remove actions for forum_thread.',24:'POST /api/admin/moderate supports owner hide/restore/publish/remove actions for forum_reply.',25:'POST /api/admin/moderate supports owner hide/restore/publish/remove actions for blog_post.',26:'POST /api/admin/moderate supports owner hide/restore/publish/remove actions for blog_comment.',29:'POST /api/admin/moderate restores hidden community/blog content to published state with an audit event.',30:'POST /api/admin/resolve-report resolves reports with audit.',31:'Owner blog posts publish immediately.',32:'Non-owner blog posts enter pending state.',33:'POST /api/admin/moderate changes persisted content status.',34:'POST /api/admin/pin-thread persists owner-controlled pin/unpin state with audit.',
41:'POST /api/admin/survey-lifecycle controls draft/active/paused/closed state.',42:'POST /api/admin/survey-lifecycle persists starts_at and ends_at scheduling fields.',43:'Survey frequency_days is owner-configurable and persisted with lifecycle updates.',44:'GET /api/admin/survey-export returns response/question rows with pseudonymous visitor identifiers and no raw IP export.',45:'GET /api/admin/survey-analytics returns response totals and per-question answer counts.',46:'POST /api/admin/survey creates surveys and questions.',47:'surveys.audience supports all/first/returning/registered.',48:'POST /api/survey/consent persists pseudonymous consent.',49:'visitor_profiles classify first/returning users without raw IP storage.',50:'survey_responses and survey_answers persist responses.',
51:'gameplay_sessions are persisted and counted.',52:'tips are persisted and shown in owner counts.',53:'GET /api/admin/user returns per-user historical/live sessions, tips and coaching experiments.',54:'egm.event.v1 metrics are computed from normalized events.',55:'GET /api/live/analysis exposes evidence-calibrated analysis.',56:'GET /api/live/replay exposes normalized evidence for the signed-in user.',57:'C014 coaching_experiments persist follow-up comparisons.',58:'GET /api/admin/coaching-trends aggregates C014 results by platform, target metric and result while excluding random credit outcomes from coaching-success scoring.',59:'GET /api/admin/evidence-quality aggregates normalized event counts, sessions and confidence by evidence type and platform.',60:'GET /api/admin/adapter-health reports per-adapter session/event activity, latest evidence and F.S.A. configuration readiness.',
63:'GET /api/admin/dashboard returns system counts.',64:'Health/API smoke routes and dashboard metrics are implemented.',68:'audit_events provides an operational audit trail.',70:'Deployment configuration is documented and surfaced through health checks.',
96:'Analysis/evidence labels enforce exact vs observed/estimate boundaries.',97:'Product copy and analysis rules prohibit profit/random-outcome guarantees.',99:'checklist table is the canonical implementation ledger.',100:'Owner Command Center UI and owner dashboard API are implemented.'
}

def default_status(i:int)->str:
    if i in IMPLEMENTED:return 'implemented'
    if i in PROVIDER_CONFIG:return 'provider_configuration_required'
    return 'modelled'

ADMIN_CAPABILITIES=[{
    'id':f'A{i:03d}','title':TITLES[i-1],'category':CATEGORIES[i-1],
    'implementation_status':default_status(i),'evidence':EVIDENCE.get(i,'Not yet implemented end-to-end; registry entry is a planned/admin requirement only.')
} for i in range(1,101)]
BY_ID={x['id']:x for x in ADMIN_CAPABILITIES}

def sync_admin_registry(con):
    for item in ADMIN_CAPABILITIES:
        row=con.execute('SELECT id FROM admin_features WHERE id=?',(item['id'],)).fetchone()
        if row:
            con.execute('UPDATE admin_features SET title=?,category=?,implementation_status=? WHERE id=?',(item['title'],item['category'],item['implementation_status'],item['id']))
        else:
            con.execute('INSERT INTO admin_features(id,title,category,implementation_status) VALUES(?,?,?,?)',(item['id'],item['title'],item['category'],item['implementation_status']))
        try:
            done=1 if item['implementation_status']=='implemented' else 0
            con.execute('UPDATE checklist SET title=?,done=?,notes=? WHERE id=?',(item['title'],done,item['evidence'],item['id']))
        except Exception:
            pass
    con.commit()

def registry_payload(rows):
    out=[]
    for row in rows:
        d=dict(row);meta=BY_ID.get(d.get('id'),{});d['evidence']=meta.get('evidence','');out.append(d)
    counts=Counter(x.get('implementation_status','unknown') for x in out)
    cats=Counter(x.get('category','Uncategorized') for x in out)
    return {'total':len(out),'summary':dict(counts),'categories':dict(cats),'features':out}
