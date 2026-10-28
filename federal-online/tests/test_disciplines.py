from fo_hub.disciplines import discipline_for, pedagogical_key


def d(subject, front=None, module=None):
    return discipline_for(subject, front, module)


def test_levels_and_variants_collapse_to_one_discipline():
    for subject in ('Biologia I', 'Biologia II', 'Biologia III', 'Biologia - Teoria',
                    'Biologia - Exercícios', 'Biologia'):
        assert d(subject, subject) == 'Biologia'
    assert d('Literatura UFPR') == d('Literatura Geral') == d('Literatura - Teoria') == 'Literatura'
    assert d('Sociologia UFPR') == d('Sociologia Geral') == 'Sociologia'
    assert d('Redação UFPR') == d('Curso de Redação') == d('Redação') == 'Redação'
    assert d('Curso de Matemática Básica') == 'Matemática'


def test_generic_containers_use_front_or_module_path():
    assert d('Aulas Gerais', 'Física', 'Extensivo UFPR 2026 > Aulas Gerais > Física > Física III') == 'Física'
    assert d('Aulas Gerais', 'Filosofia UFPR', 'x') == 'Filosofia'
    assert d('Aprofundamento - Extras', 'Aprofundamento', 'Conteúdos Extras > Biologia > Aprofundamento') == 'Biologia'
    assert d('História Geral - Extras', 'História Geral', 'Conteúdos Extras') == 'História'
    assert d('Reprodução - Foco ENEM - Extras', 'Reprodução - Foco ENEM', 'Conteúdos Extras > Biologia > Reprodução') == 'Biologia'


def test_non_academic_groups_are_explicit_not_guessed():
    for subject in ('Anki - Flashcards', 'Método Pomodoro', 'Caderno de erros', 'Introdução',
                    'II - Momento da prova', 'Dicas finais', 'Métodos de Estudo'):
        assert d(subject, subject, 'Métodos de Estudo') == 'Métodos de Estudo'
    assert d('I - Rotina', 'I - Rotina', 'Diário dos aprovados - Medicina UFPR') == 'Métodos de Estudo'
    assert d('Simulado 10: 27 a 29 de ago', None, 'Mini Simulados - Medicina UFPR') == 'Simulados'
    assert d('Simuladão UFPR #01') == 'Simulados'
    assert d('Curso de Ciências Básica') == 'Ciências Básicas'
    assert d('Algo desconhecido', None, 'Nada') == 'Outros'


def test_word_boundaries_avoid_substring_false_positives():
    # "Física" must not match inside an unrelated word; accents are normalised.
    assert d('FISICA I') == 'Física'
    assert d('Geografia', None, 'Fisicamente > nada') == 'Geografia'


def test_pedagogical_key_orders_levels_then_lesson_numbers():
    rows = [
        {'subject': 'Biologia II', 'title': 'Aula 02 - B', 'module': 'Aulas Gerais > Biologia > Biologia II'},
        {'subject': 'Biologia I', 'title': 'Aula 10 - C', 'module': 'Aulas Gerais > Biologia > Biologia I'},
        {'subject': 'Biologia I', 'title': 'Aula 2 - A', 'module': 'Aulas Gerais > Biologia > Biologia I'},
        {'subject': 'Biologia I', 'title': 'Aula extra - Z', 'module': 'Aulas Gerais > Biologia > Biologia I'},
    ]
    ordered = sorted(rows, key=pedagogical_key)
    assert [r['title'] for r in ordered] == ['Aula 2 - A', 'Aula 10 - C', 'Aula extra - Z', 'Aula 02 - B']
