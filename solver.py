"""Find a small family of k-subsets covering every j-subset."""

from itertools import combinations
from dataclasses import dataclass
from math import comb, gcd
from random import Random
from time import monotonic


@dataclass
class Solution:
    groups: list
    lower_bound: int
    optimal: bool


class _DeadlineReached(Exception):
    pass


def _check_deadline(deadline):
    if monotonic() >= deadline:
        raise _DeadlineReached


def validate(m, n, k, j, s):
    if not (45 <= m <= 54 and 7 <= n <= 25 and 4 <= k <= 7 and 3 <= s <= j <= k <= n):
        raise ValueError("Parameter ranges: 45 <= m <= 54, 7 <= n <= 25, 4 <= k <= 7, 3 <= s <= j <= k <= n.")


def _masks(bits, size):
    for subset in combinations(bits, size):
        yield sum(subset)


def _coverage_size(n, k, j, s):
    return sum(comb(k, r) * comb(n-k, j-r) for r in range(s, j+1))


def _lower_bound(n, k, j, s, target_count, coverage_size):
    bound = (target_count + coverage_size - 1) // coverage_size
    if j == s:
        # Count how many blocks must contain each individual element, recursively.
        recursive = 1
        for offset in reversed(range(j)):
            recursive = ((n-offset) * recursive + k-offset-1) // (k-offset)
        bound = max(bound, recursive)
    return bound


def _covered(group, bits, j, s, targets):
    inside = [bit for bit in bits if group & bit]
    outside = [bit for bit in bits if not group & bit]
    limit = _coverage_size(len(bits), len(inside), j, s)
    if limit >= len(targets):
        yield from (target for target in targets if (group & target).bit_count() >= s)
        return
    if len(inside) == j == s+1:
        yield group
        for bit in inside:
            partial = group ^ bit
            for extra in outside:
                yield partial | extra
        return
    for r in range(s, min(len(inside), j) + 1):
        for shared in _masks(inside, r):
            for rest in _masks(outside, j-r):
                yield shared | rest


def _witt_cover(n, k, j, s, bits):
    if n not in (12, 13) or (k, j, s) != (6, 5, 5):
        return None
    # On the projective line over F_11, use translation and x -> -1/x.
    # The orbit of the quadratic residues together with infinity is S(5,6,12).
    infinity = 11
    first = (1, 3, 4, 5, 9, infinity)
    invert = [infinity] + [(-pow(x, -1, 11)) % 11 for x in range(1, 11)] + [0]
    hexads = {first}
    pending = [first]
    while pending:
        block = pending.pop()
        shifted = tuple(sorted((x+1) % 11 if x != infinity else x for x in block))
        inverted = tuple(sorted(invert[x] for x in block))
        for image in (shifted, inverted):
            if image not in hexads:
                hexads.add(image)
                pending.append(image)
    groups = {sum(bits[x] for x in block) for block in hexads}
    if n == 13:
        # Extend recursively using the derived S(4,5,11), S(3,4,10),
        # S(2,3,9), and a five-pair cover of the final nine points.
        parent_groups = groups.copy()
        for fixed in (1 << 11, (1 << 11) | (1 << 10), (1 << 11) | (1 << 10) | (1 << 9)):
            groups.update((group ^ fixed) | (fixed << 1)
                          for group in parent_groups if group & fixed == fixed)
        added = sum(bits[point] for point in range(9, 13))
        groups.update(added | bits[x] | bits[(x+1) % 9] for x in range(0, 9, 2))
    return sorted(groups)


def _orbit_cover(bits, k, j, s, targets, order, xor, deadline, rng):
    """Choose whole symmetry orbits, so each representative stands for its orbit."""
    n = len(bits)
    universe = (1 << n) - 1

    def translate(mask, step):
        if not xor:
            shift = step * (n // order)
            return ((mask << shift) | (mask >> (n-shift))) & universe
        image = 0
        while mask:
            bit = mask & -mask
            image |= 1 << ((bit.bit_length()-1) ^ step)
            mask ^= bit
        return image

    positions = {}
    orbit_count = 0
    for target in targets:
        _check_deadline(deadline)
        if target not in positions:
            flag = 1 << orbit_count
            orbit_count += 1
            for step in range(order):
                positions[translate(target, step)] = flag

    visited = set()
    choices = []
    for group in _masks(bits, k):
        _check_deadline(deadline)
        if group in visited:
            continue
        family = sorted({translate(group, step) for step in range(order)})
        visited.update(family)
        hits = 0
        for target in _covered(group, bits, j, s, targets):
            hits |= positions[target]
        choices.append((hits, family))

    best = None
    for attempt in range(8):
        if attempt:
            rng.shuffle(choices)
        uncovered = (1 << orbit_count) - 1
        groups = []
        while uncovered:
            if monotonic() >= deadline:
                return best
            hits, family = max(
                choices, key=lambda entry: (entry[0] & uncovered).bit_count() / len(entry[1])
            )
            uncovered &= ~hits
            groups.extend(family)
        if best is None or len(groups) < len(best):
            best = groups
    return best


def _symmetry_seed(bits, k, j, s, targets, coverage_size, deadline):
    n = len(bits)
    if len(targets) > 12_000 or comb(n, k) > 20_000:
        return None
    actions = [(n, False)]
    actions.extend((order, True) for order in (16, 8, 4) if n % order == 0)
    best = None
    try:
        for order, xor in actions:
            if comb(n, k) * coverage_size > order * 1_000_000:
                continue
            groups = _orbit_cover(
                bits, k, j, s, targets, order, xor, deadline, Random(23)
            )
            if groups is not None and (best is None or len(groups) < len(best)):
                best = groups
    except _DeadlineReached:
        pass
    return best


def _greedy_full(bits, k, j, s, targets, passes, rng, deadline):
    groups = list(_masks(bits, k))
    positions = {target: divmod(index, 8) for index, target in enumerate(targets)}
    covers = []
    for group in groups:
        if monotonic() >= deadline:
            return groups
        packed = bytearray((len(targets) + 7) // 8)
        for target in _covered(group, bits, j, s, targets):
            byte, bit = positions[target]
            packed[byte] |= 1 << bit
        covers.append(int.from_bytes(packed, "little"))
    best = groups
    order = list(range(len(groups)))
    for attempt in range(passes):
        if attempt:
            rng.shuffle(order)
        uncovered = (1 << len(targets)) - 1
        selected = []
        while uncovered and len(selected) < len(best):
            if monotonic() >= deadline:
                return best
            index = max(order, key=lambda i: (covers[i] & uncovered).bit_count())
            uncovered &= ~covers[index]
            selected.append(groups[index])
        if not uncovered and len(selected) < len(best):
            best = selected
    return best


def _greedy_large(bits, k, j, s, targets, rng, deadline, fallback=None):
    # Keep the live targets in a dense list for uniform sampling and O(1) removal.
    live = targets.copy()
    uncovered = {target: index for index, target in enumerate(live)}
    coverage_size = _coverage_size(len(bits), k, j, s)
    groups = []
    while live:
        if monotonic() >= deadline:
            if fallback is not None:
                return fallback
            for target in live:
                shared = target
                for _ in range(j-s):
                    shared ^= shared & -shared
                extra = (bit for bit in bits if not shared & bit)
                groups.append(shared | sum(next(extra) for _ in range(k-s)))
            return list(dict.fromkeys(groups))
        sample = rng.sample(live, min(len(live), 96))
        candidates = set()
        for target in sample[:8]:
            inside = [bit for bit in bits if target & bit]
            outside = [bit for bit in bits if not target & bit]
            candidates.add(target | sum(rng.sample(outside, k-j)))
            for _ in range(3):
                shared = rng.randint(max(s, k-len(outside)), j)
                candidates.add(sum(rng.sample(inside, shared)) + sum(rng.sample(outside, k-shared)))
        finalists = sorted(candidates)
        if coverage_size > 200:
            finalists.sort(key=lambda g: sum((g & t).bit_count() >= s for t in sample), reverse=True)
            finalists = finalists[:8]
        best = []
        for candidate in finalists:
            hits = [t for t in _covered(candidate, bits, j, s, uncovered) if t in uncovered]
            if len(hits) > len(best):
                group, best = candidate, hits
        for target in best:
            index = uncovered.pop(target)
            tail = live.pop()
            if index < len(live):
                live[index] = tail
                uncovered[tail] = index
        groups.append(group)
    return groups


def _prune(groups, bits, j, s, targets, deadline):
    counts = dict.fromkeys(targets, 0)
    for group in groups:
        if monotonic() >= deadline:
            return groups
        for target in _covered(group, bits, j, s, targets):
            counts[target] += 1
    kept = []
    for group in reversed(groups):
        if monotonic() >= deadline:
            return groups
        hits = list(_covered(group, bits, j, s, targets))
        if all(counts[target] > 1 for target in hits):
            for target in hits:
                counts[target] -= 1
        else:
            kept.append(group)
    return kept[::-1]


def _branch_cover(covers, target_count, limit, deadline):
    """Solve the binary covering constraints with at most limit selected groups."""
    options = [[] for _ in range(target_count)]
    for group, mask in covers.items():
        _check_deadline(deadline)
        while mask:
            bit = mask & -mask
            options[bit.bit_length()-1].append(group)
            mask ^= bit
    failed = {}

    def search(uncovered, remaining):
        _check_deadline(deadline)
        if not uncovered:
            return []
        if not remaining or failed.get(uncovered, -1) >= remaining:
            return None
        pending = uncovered
        pivot = None
        while pending:
            bit = pending & -pending
            choices = options[bit.bit_length()-1]
            if pivot is None or len(choices) < len(pivot):
                pivot = choices
            pending ^= bit
        demand = uncovered.bit_count()
        if max((mask & uncovered).bit_count() for mask in covers.values()) * remaining >= demand:
            ordered = sorted(pivot, key=lambda g: (covers[g] & uncovered).bit_count(), reverse=True)
            for group in ordered:
                result = search(uncovered & ~covers[group], remaining-1)
                if result is not None:
                    return [group, *result]
        if len(failed) < 100_000:
            failed[uncovered] = remaining
        return None

    return search((1 << target_count)-1, limit)


def _cover_candidates(bits, k, j, s, targets, deadline):
    """Enumerate all candidates incident to at least one requested target."""
    candidates = {}
    for index, target in enumerate(targets):
        inside = [bit for bit in bits if target & bit]
        outside = [bit for bit in bits if not target & bit]
        flag = 1 << index
        for shared in range(max(s, k-len(outside)), j+1):
            for overlap in _masks(inside, shared):
                _check_deadline(deadline)
                for extra in _masks(outside, k-shared):
                    group = overlap | extra
                    candidates[group] = candidates.get(group, 0) | flag
    return candidates


def _improve(groups, bits, k, j, s, targets, lower, deadline, rng):
    if len(groups) == lower:
        return groups, lower
    # Run the unrestricted model when its search state fits in memory.
    if len(targets) <= 256 and comb(len(bits), k) <= 2000:
        # Search the smallest allowed cardinality first to establish a proof early.
        try:
            covers = _cover_candidates(bits, k, j, s, targets, deadline)
            while lower < len(groups):
                candidate = _branch_cover(covers, len(targets), lower, deadline)
                if candidate is not None:
                    return candidate, lower
                lower += 1
        except _DeadlineReached:
            pass
        return groups, lower

    # Fix most existing groups, then solve all residual constraints exactly.
    counts = dict.fromkeys(targets, 0)
    cache = {}
    try:
        for group in groups:
            _check_deadline(deadline)
            hits = tuple(_covered(group, bits, j, s, targets))
            if (len(cache) + 1) * len(hits) > 3_000_000:
                break
            cache[group] = hits
            for target in hits:
                counts[target] += 1
        if len(cache) != len(groups):
            # A large dense matrix is handled by solving a smaller residual model.
            return _improve_dense(groups, bits, k, j, s, targets, lower, deadline, rng)
        while len(groups) > lower:
            _check_deadline(deadline)
            anchor = rng.choice(groups)
            neighbors = rng.sample(groups, min(40, len(groups)))
            neighbors.sort(key=lambda group: (anchor & group).bit_count(), reverse=True)
            size = rng.randint(2, min(6, len(groups)))
            peers = [group for group in neighbors if group != anchor]
            removed = {anchor, *peers[:size-1]}
            touched = {}
            for group in removed:
                for target in cache[group]:
                    touched[target] = touched.get(target, 0) + 1
            residual = [target for target, count in touched.items() if count == counts[target]]
            replacement = _repair(bits, k, j, s, residual, len(removed)-1, deadline)
            if replacement is None:
                continue
            for target, count in touched.items():
                counts[target] -= count
            for group in replacement:
                cache[group] = tuple(_covered(group, bits, j, s, targets))
                for target in cache[group]:
                    counts[target] += 1
            for group in removed.difference(replacement):
                del cache[group]
            groups = [group for group in groups if group not in removed] + replacement
    except _DeadlineReached:
        pass
    return groups, lower


def _repair(bits, k, j, s, residual, limit, deadline):
    if not residual:
        return []
    if len(residual) > 96:
        return None
    attempt_deadline = min(deadline, monotonic() + 0.08)
    try:
        covers = _cover_candidates(bits, k, j, s, residual, attempt_deadline)
        return _branch_cover(covers, len(residual), limit, attempt_deadline)
    except _DeadlineReached:
        return None


def _improve_dense(groups, bits, k, j, s, targets, lower, deadline, rng):
    while len(groups) > lower:
        if monotonic() >= deadline:
            break
        removed = set(rng.sample(groups, min(len(groups), 3)))
        keep = [group for group in groups if group not in removed]
        residual = set(targets)
        for group in keep:
            if monotonic() >= deadline:
                return groups, lower
            residual.difference_update(list(_covered(group, bits, j, s, residual)))
            if not residual:
                break
        replacement = _repair(bits, k, j, s, sorted(residual), len(removed)-1, deadline)
        if replacement is not None:
            groups = keep + replacement
    return groups, lower


def _residue_cover(bits, k):
    # For gcd(n,k)=1, a nonzero cyclic translation cannot leave a k-set invariant.
    # Replace one point by its translate to make the block sum zero modulo n.
    n = len(bits)
    return [sum(bits[x] for x in group)
            for group in combinations(range(n), k) if sum(group) % n == 0]


def _verify(groups, bits, j, s, targets, coverage_size):
    if len(groups) * coverage_size > 4_000_000:
        faces = set()
        for group in groups:
            faces.update(_masks([bit for bit in bits if group & bit], s))
        for target in targets:
            if not any(face in faces for face in _masks([bit for bit in bits if target & bit], s)):
                raise RuntimeError("Coverage verification failed: an uncovered target was found.")
        return
    uncovered = set(targets)
    for group in groups:
        uncovered.difference_update(list(_covered(group, bits, j, s, uncovered)))
        if not uncovered:
            return
    raise RuntimeError(f"Coverage verification failed: {len(uncovered)} targets remain uncovered.")


def solve_timed(samples, k, j, s, seconds=3):
    """Find a feasible cover and improve it until the search deadline."""
    start = monotonic()
    deadline = start + seconds
    seed_deadline = start + seconds * 0.75
    bits = [1 << index for index in range(len(samples))]
    if k == j == s:
        groups = list(combinations(samples, k))
        return Solution(groups, len(groups), True)
    targets = list(_masks(bits, j))
    rng = Random(23)
    candidate_count = comb(len(bits), k)
    matrix_size = candidate_count * len(targets)
    coverage_size = _coverage_size(len(bits), k, j, s)
    lower = _lower_bound(len(bits), k, j, s, len(targets), coverage_size)
    groups = _witt_cover(len(bits), k, j, s, bits)
    if groups is None:
        symmetry = _symmetry_seed(
            bits, k, j, s, targets, coverage_size, start + min(seconds * 0.40, 1)
        )
        matrix_budget = min(75_000_000, int(seconds * 4_000_000))
        if symmetry is not None and len(symmetry) == lower:
            groups = symmetry
        elif matrix_size <= matrix_budget and candidate_count * coverage_size <= 10_000_000:
            passes = 12 if matrix_size <= 2_500_000 else 5
            groups = _greedy_full(bits, k, j, s, targets, passes, rng, seed_deadline)
        else:
            fallback = symmetry
            if fallback is None and candidate_count > 20_000 and k == j == s+1 and gcd(len(bits), k) == 1:
                fallback = _residue_cover(bits, k)
            groups = _greedy_large(bits, k, j, s, targets, rng, seed_deadline, fallback)
        if symmetry is not None and len(symmetry) < len(groups):
            groups = symmetry
        if len(groups) * coverage_size <= 10_000_000:
            groups = _prune(groups, bits, j, s, targets, seed_deadline)
        groups, lower = _improve(groups, bits, k, j, s, targets, lower, deadline, rng)
    _verify(groups, bits, j, s, targets, coverage_size)
    decoded = [tuple(sample for bit, sample in zip(bits, samples) if group & bit) for group in groups]
    return Solution(decoded, lower, len(groups) == lower)


def solve(samples, k, j, s):
    return solve_timed(samples, k, j, s).groups
