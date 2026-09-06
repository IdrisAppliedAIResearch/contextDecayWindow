"""Amendment 002's single shared-dispatch development variant."""
from corpus import make_session as original, identity


def make_session(seed):
    session, labels, ledger = original(seed)
    names = [labels[q['id']]['rationale']['subject'] for q in session['probes']]
    idmap = {}
    for episode in session['episodes']:
        old_id = episode['id']
        if episode['turn_number'] <= 108:
            indices = [0, 2, 4] if episode['turn_number'] % 2 else [1, 3, 5]
            subjects = ', '.join(f'"{names[i]}"' for i in indices)
            episode['user_message'] += (
                f'\nThe dispatch audit for {subjects} reviewed delivery-location records, '
                'including the office, warehouse, studio, depot, workshop, laboratory, '
                'annex and hangar. This audit supplies no new delivery-location value '
                'and changes no instruction for any project.'
            )
            episode['id'] = identity({k: v for k, v in episode.items() if k != 'id'})
        idmap[old_id] = episode['id']
    for label in labels.values():
        label['gold_ids'] = [idmap[x] for x in label['gold_ids']]
    return session, labels, ledger
