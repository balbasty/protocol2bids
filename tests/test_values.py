import pytest

from protocol2bids import values as V


@pytest.mark.parametrize('text,expected', [
    ('2000 ms', 2.0), ('2.88 ms', 0.00288), ('2000 [ms]', 2.0),
    ('0.5 s', 0.5), ('794', 0.794),
])
def test_seconds(text, expected):
    assert V.seconds(text) == pytest.approx(expected)


@pytest.mark.parametrize('text,expected', [
    ('6/8', 0.75), ('7/8', 0.875), ('Off', 1.0), ('75 %', 0.75),
])
def test_fraction(text, expected):
    assert V.fraction(text) == pytest.approx(expected)


@pytest.mark.parametrize('text,expected', [
    ('A >> P', 'AP'), ('P >> A', 'PA'), ('R>>L', 'RL'),
    ('F >> H', 'IS'), ('H >> F', 'SI'),
])
def test_direction(text, expected):
    assert V.direction(text) == expected


def test_orientation():
    assert V.orientation('Transversal') == ('T', [])
    assert V.orientation('T > C-23.0') == ('T', [('C', -23.0)])
    assert V.orientation('Sag>Cor(-10.2)>Tra(3.1)') == \
        ('S', [('C', -10.2), ('T', 3.1)])


def test_misc():
    assert V.quantity('240 [mm]', 'mm') == 240
    assert V.quantity('2520 Hz/Px', 'Hz/Px') == 2520
    assert V.unit('0 [%]') == '%'
    assert V.position('L0.0 A20.0 H0.0 mm') == {'L': 0, 'A': 20, 'H': 0}
    assert V.position('Isocenter') == {}
    assert V.matrix('256x192') == [256, 192]
    assert V.boolean('On') is True and V.boolean('0') is False
    with pytest.raises(ValueError):
        V.number('None')
