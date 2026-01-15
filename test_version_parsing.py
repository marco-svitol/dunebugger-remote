#!/usr/bin/env python3
"""
Test script for parse_semver function
"""

def parse_semver(ver_str):
    """Parse semantic version into comparable tuple"""
    if '-' in ver_str:
        base, pre = ver_str.split('-', 1)
    else:
        base, pre = ver_str, None
    
    try:
        base_parts = tuple(int(x) for x in base.split('.'))
    except ValueError:
        base_parts = (0, 0, 0)
    
    if pre:
        pre_clean = pre.split('.dev')[0].split('.dirty')[0]
        if '.' in pre_clean:
            pre_name, pre_num = pre_clean.rsplit('.', 1)
            try:
                pre_tuple = (pre_name, int(pre_num))
            except ValueError:
                pre_tuple = (pre_clean, 0)
        else:
            pre_tuple = (pre_clean, 0)
        return (base_parts, 0, pre_tuple)
    else:
        return (base_parts, 1, None)


def main():
    # Test cases
    test_cases = [
        ('1.0.0', 'Release version'),
        ('1.0.0-beta.3', 'Prerelease version'),
        ('1.0.0-beta.3.dev2', 'Dev prerelease'),
        ('2.1.5-alpha.1', 'Alpha prerelease'),
    ]

    print('Testing parse_semver function:')
    print('=' * 60)
    for version, description in test_cases:
        result = parse_semver(version)
        print(f'{version:20} ({description})')
        print(f'  -> {result}')
        print()

    # Test comparison
    print('Testing version comparisons:')
    print('=' * 60)
    comparisons = [
        ('1.0.0-beta.2', '1.0.0-beta.3', 'Newer beta should be greater'),
        ('1.0.0-beta.3', '1.0.0', 'Release should be greater than prerelease'),
        ('1.0.0', '1.0.1', 'Newer patch should be greater'),
        ('1.0.0-beta.3.dev2', '1.0.0-beta.3', 'Prerelease should be equal (dev ignored)'),
    ]

    for v1, v2, description in comparisons:
        p1 = parse_semver(v1)
        p2 = parse_semver(v2)
        result = p2 > p1
        symbol = '✓' if result else '✗'
        print(f'{symbol} {v1} < {v2}: {result} ({description})')


if __name__ == '__main__':
    main()
