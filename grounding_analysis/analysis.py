import sys
import random
from collections import Counter
from indra.statements import Complex
from indra.sources import indra_db_rest
from indra.databases import hgnc_client, get_identifiers_url


def get_statements(db_ns, db_id, ev_limit=100):
    ip = indra_db_rest.get_statements(agents=['%s@%s' % (db_id, db_ns)],
                                      ev_limit=ev_limit)
    return ip.statements


def get_raw_strings(stmts, db_ns, db_id):
    raw_strings = []
    for stmt in stmts:
        # Raw annotations for Complexes are not reliable
        # due to possible reordering
        if isinstance(stmt, Complex):
            continue
        for idx, agent in enumerate(stmt.agent_list()):
            if agent is not None and agent.db_refs.get(db_ns) == db_id:
                for ev in stmt.evidence:
                    agents = ev.annotations['agents']
                    text = agents['raw_text'][idx]
                    if text:
                        raw_strings.append(text)
    return raw_strings


def get_top_counts(raw_strings, threshold=0.8):
    cnt = Counter(raw_strings)
    ranked_list = cnt.most_common()
    total = sum(c for e, c in ranked_list)
    top_list = []
    cum_sum = 0
    for element, count in ranked_list:
        cum_sum += (count / total)
        top_list.append((element, count))
        if cum_sum >= threshold:
            break
    return top_list


def get_hgnc_ids():
    # All HGNC IDs in the client
    # return sorted(list(hgnc_client.hgnc_names.keys()))

    # All HGNC IDs for which we have preassembled stmts in the DB
    with open('hgnc_ids.txt', 'r') as fh:
        hgnc_ids = [l.strip() for l in fh.readlines()]
        return hgnc_ids


def generate_report(genes, top_lists, fname):
    html = '<table border=1>\n%s\n</table>'
    rows = []
    for gene, top_list in sorted(zip(genes, top_lists),
                                 key=lambda x: sum([y[1] for y in x[1]]),
                                 reverse=True):
        row = '<tr><td>%s</td><td>%s</td></tr>'
        gene_entry = '<a href="%s">%s</a>' % \
            (get_identifiers_url('HGNC', gene),
             hgnc_client.get_hgnc_name(gene))
        top_list_entries = []
        for element, count in top_list:
            url = ('https://db.indra.bio/statements/from_agents?'
                   'agent0=%s@TEXT&format=html' % element)
            top_list_entries.append('<a href="%s">%s</a> (%d)' %
                                    (url, element, count))
        top_list_entry = ', '.join(top_list_entries)
        row = row % (gene_entry, top_list_entry)
        rows.append(row)
    html = html % ('\n'.join(rows))
    with open(fname, 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    genes = get_hgnc_ids()
    genes = [random.choice(genes) for _ in range(100)]
    top_lists = []
    for gene in genes:
        stmts = get_statements('HGNC', gene)
        raw_strings = get_raw_strings(stmts, 'HGNC', gene)
        top_list = get_top_counts(raw_strings)
        top_lists.append(top_list)
    generate_report(genes, top_lists, 'report.html')
