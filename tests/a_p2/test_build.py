def test_accepted_gide_identity_requires_exact_loader_match():
    from tools.a_p2.build import accepted_gide_pairs
    proposal = [{'run': 'r1', 'patient': 'p1'}, {'run': 'r2', 'patient': 'p2'}]
    patients = {'p1': 'uid1', 'p2': 'uid2'}
    assert accepted_gide_pairs(proposal, patients, {'r1': 'uid1', 'r2': 'uid2'}) == {'uid1': 'r1', 'uid2': 'r2'}
    assert accepted_gide_pairs(proposal, patients, {'r1': 'wrong', 'r2': 'uid2'}) == {'uid2': 'r2'}
