"""Independent mathematical receipt for BT.2124-0's Annex-4 input.

Only stdlib rational/Decimal arithmetic: no production, test or renderer imports.
Run directly to print JSON; this is not a unit test or a rendering probe.
Equations: Annex 2 conversion 3 (PQ decode), Annex 1 section 2 steps 1-4.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
import json


CONSTANTS = {
    'm1': Fraction(2610, 16384),
    'm2': Fraction(2523 * 128, 4096),
    'c1': Fraction(3424, 4096),
    'c2': Fraction(2413 * 32, 4096),
    'c3': Fraction(2392 * 32, 4096),
}
RGB_LMS = ((1688, 2146, 262), (683, 2951, 462), (99, 309, 3688))
LMS_ITP = ((Fraction(1, 2), Fraction(1, 2), Fraction(0)),
           (Fraction(6610, 8192), Fraction(-13613, 8192), Fraction(7003, 8192)),
           (Fraction(17933, 4096), Fraction(-17390, 4096), Fraction(-543, 4096)))


def derive(precision):
    with localcontext() as ctx:
        ctx.prec = precision

        def decimal(rational):
            return Decimal(rational.numerator) / Decimal(rational.denominator)

        m1, m2, c1, c2, c3 = (decimal(CONSTANTS[k]) for k in ('m1', 'm2', 'c1', 'c2', 'c3'))

        def decode(signal):
            root = ctx.power(signal, 1 / m2)
            return ctx.power(max(root - c1, Decimal(0)) / (c2 - c3 * root), 1 / m1)

        def encode(relative_light):
            power = ctx.power(relative_light, m1)
            return ctx.power((c1 + c2 * power) / (1 + c3 * power), m2)

        def transform(relative_rgb):
            relative_lms = tuple(sum(Decimal(c) * v for c, v in zip(row, relative_rgb)) / 4096
                                 for row in RGB_LMS)
            nonlinear_lms = tuple(encode(v) for v in relative_lms)
            itp = tuple(sum(decimal(c) * v for c, v in zip(row, nonlinear_lms)) for row in LMS_ITP)
            return relative_lms, nonlinear_lms, itp

        signals = tuple(decimal(Fraction(code, 1023)) for code in (296, 201, 582))
        relative_rgb = tuple(decode(v) for v in signals)
        relative_lms, nonlinear_lms, itp = transform(relative_rgb)
        # Diagnostics only: do not silently use displayed rounded intermediates
        # as the oracle for the exact full-range digital input.
        rounded_signal_rgb = tuple(decode(Decimal(v)) for v in ('0.2893', '0.1964', '0.5689'))
        displayed_rgb = tuple(Decimal(v) / 10000 for v in ('8.753', '2.291', '181.3'))
        return {
            'precision': precision,
            'normalized_pq_rgb': [str(v) for v in signals],
            'linear_rgb_nits': [str(v * 10000) for v in relative_rgb],
            'linear_lms_nits': [str(v * 10000) for v in relative_lms],
            'nonlinear_lms': [str(v) for v in nonlinear_lms],
            'itp': [str(v) for v in itp],
            'diagnostic_rounded_signal_rgb_nits': [str(v * 10000) for v in rounded_signal_rgb],
            'diagnostic_displayed_linear_rgb_itp': [str(v) for v in transform(displayed_rgb)[2]],
        }


def receipt():
    calculations = [derive(p) for p in (80, 120)]
    with localcontext() as ctx:
        ctx.prec = 130
        differences = [abs(Decimal(a) - Decimal(b))
                       for a, b in zip(calculations[0]['itp'], calculations[1]['itp'])]
        published = tuple(Decimal(v) for v in ('0.3554', '0.1346', '-0.1613'))
        normative = tuple(Decimal(v) for v in calculations[1]['itp'])
        return {
            'schema': 1,
            'kind': 'independent-mathematical-derivation-not-unit-or-render',
            'standard': 'ITU-R BT.2124-0 (01/2019; February 2020 editorial publication)',
            'url': 'https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.2124-0-201901-I!!PDF-E.pdf',
            'pdf_sha256': 'cad1e382516da511811c5205e5abe1b0b97999cf4722d4854a439389eff54470',
            'citations': ['Annex 2 conversion 3: full-range PQ RGB decode',
                          'Annex 1 section 2 steps 1-4: RGB to LMS, PQ on LMS, I/CT/CP, T=CT/2',
                          'Annex 4 section 1: informative digital-input example'],
            'codes': [296, 201, 582],
            'divisor': 1023,
            'pq_constants_rational': {k: str(v) for k, v in CONSTANTS.items()},
            'rgb_lms_integer_rows_divisor_4096': RGB_LMS,
            'lms_itp_rational_rows': [[str(v) for v in row] for row in LMS_ITP],
            'calculations': calculations,
            'precision_absolute_differences_itp': [str(v) for v in differences],
            'stable_to_absolute_1e-70': max(differences) < Decimal('1e-70'),
            'normative_itp_16_decimal_places': [str(v.quantize(Decimal('1e-16'))) for v in normative],
            'normative_minus_informative_itp': [str(a - b) for a, b in zip(normative, published)],
            'production_imports': False,
            'unit_or_renderer_executions': 0,
        }


if __name__ == '__main__':
    print(json.dumps(receipt(), indent=2) + '\n', end='')
