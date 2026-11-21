# encoding: utf-8
"""
``StandardVersion`` parses a version string and presents it in multiple common formats, compatible with pythonic SemVer.

Handles:

- Any number of version segments (1.0, 1.2.3, 1.2.3.4, ...)
- Optional 'v' prefix.
- Preserves padded ints in main version part (v0.001.023)
- Optional suffix:

  - separator is always normalized to '-': v1.2.3-alpha, not v1.2.3.alpha
  - PIP pre-releases (a1, b2, rc3) are converted to nicer alpha1, beta2, RC3.
"""

from .___package_meta import __version__

from typing_clean import _A, _C, _O, _U, _Dict, _Generator, _Tuple, _NamedTuple, _Match

import os as _os
import re as _re


_T_Matcher = _C[[str], _O[_Match[str]]]
_T_Path = _U[str, _os.PathLike]

_re_padded_int = _re.compile(
	r'^(?P<pad>0*)'
	r'(?P<int>[1-9][0-9]*)?'
	r'$',
	flags=_re.IGNORECASE
).match


class _PadInt(_NamedTuple):
	"""Internal utility class: int with a preserved 0-padding."""
	number: int
	pad: int = 0

	@staticmethod
	def parse(int_str: str) -> '_PadInt':
		assert isinstance(int_str, str) and int_str.strip()
		match = _re_padded_int(int_str)
		if not match:
			raise ValueError(f'Invalid number-string: {int_str!r}')
		pad = len(match.group('pad'))
		try:
			int_group = match.group('int')
		except IndexError:
			int_group = None
		if not int_group:
			return _PadInt(0, max(pad - 1, 0))
		return _PadInt(int(int_group), pad)

	def format(self) -> str:
		pad_str = '0' * max(self.pad, 0)
		return f'{pad_str}{self.number}'


_re_whole_version = _re.compile(  # Whole version string -> num/suffix groups
	r'(?:[vV][^a-zA-Z0-9]*)?'  # v + optional punctuation
	r'(?P<num>'  # the main version number group
	r'[0-9]+'  # first part
	r'(?:[^a-zA-Z0-9]+[0-9]+)*'  # all other numeric parts with separators
	r')'
	r'[^a-zA-Z0-9]*'  # optional suffix-separator
	r'(?P<suffix>'
	r'[a-zA-Z]+'
	r'.*?'
	r')?$',
	flags=_re.IGNORECASE
).match
# Python's re.match acts weirdly with groups
# when a (possibly recurring) group is inside non-capturing optional one.
# Thus, we have to extract segments in a loop, one by one:
_re_number_seg = _re.compile(  # Parse only numeric group into actual numbers
	r'(?P<first>[0-9]+)'  # First number
	r'(?:'
	r'[^a-zA-Z0-9]+'  # Any non-ASCII separator
	r'(?P<remainder>.*?)'  # The remainder
	r')?$',
	flags=_re.IGNORECASE
).match
_re_suffix_seg = _re.compile(  # Parse only suffix group into ASCII parts
	r'(?P<first>[a-zA-Z0-9]+)'
	r'(?:'
	r'[^a-zA-Z0-9]+'  # Any non-ASCII separator
	r'(?P<remainder>.*?)'  # The remainder
	r')?$',
	flags=_re.IGNORECASE
).match


class _ParsedVersion(_NamedTuple):
	"""Initial rough separation of version-string into ints and suffix parts."""
	numbers: _Tuple[_PadInt, ...]
	suffix: _Tuple[str, ...] = tuple()

	@staticmethod
	def __parse_group_parts(
		group: str, seg_extractor: _T_Matcher,
		what='base version'
	) -> _Generator[str, _A, None]:
		while group:
			match = seg_extractor(group)
			if not match:
				raise ValueError(f'Invalid remainder of {what}: {group!r}')
			yield match.group('first')
			try:
				group = match.group('remainder')
			except IndexError:
				break

	@staticmethod
	def parse(version_str: str) -> '_ParsedVersion':
		# version_str = 'v.1.2.3a1 aaa'
		# version_str = 'v.1.2.3'
		assert isinstance(version_str, str) and version_str.strip()
		match = _re_whole_version(version_str)
		if not match:
			raise ValueError(f'Invalid version string: {version_str!r}')
		num_group = match.group('num')
		try:
			suffix_group = match.group('suffix')
		except IndexError:
			suffix_group = ''

		int_parse = _PadInt.parse
		numbers = tuple(
			int_parse(x) for x in
			_ParsedVersion.__parse_group_parts(num_group, _re_number_seg)
		)
		suffix_parts = tuple(
			_ParsedVersion.__parse_group_parts(suffix_group, _re_suffix_seg, 'suffix')
		)
		return _ParsedVersion(numbers, suffix_parts)


# _ParsedVersion.parse('v.0.00.01.020.00300a1 aaa')
# _ParsedVersion.parse('v0')
# _ParsedVersion.parse('0')
# _ParsedVersion.parse('v0.001b1')


# https://peps.python.org/pep-0440/#pre-releases
_pre_v_converters: _Dict[str, _T_Matcher] = {
	_formatter: _re.compile(_pattern, flags=_re.IGNORECASE).match
	for _formatter, _pattern in (
		('alpha{}', r'a(?:lpha)?([0-9]*)$'),
		('beta{}', r'b(?:eta)?([0-9]*)$'),
		('RC{}', r'r?c([0-9]*)$'),
	)
}
_pre_v_matcher = _re.compile(
	r'(?:alpha|beta|RC)[0-9]*$',
	flags=_re.IGNORECASE
).match


def _convert_suffix_to_human_readable(suffix: str) -> str:
	"""
	Standardize suffix parts into full format:

	- ``a0`` / ``alpha0`` / ``ALPHA0`` -> always ``alpha0``
	- ``b1`` / ``beta1`` / ``BETA1`` -> always ``beta1``,
	- ``r1`` / ``rc1`` / ``RC1`` -> always ``RC1``
	"""
	for format_str, matcher in _pre_v_converters.items():
		match = matcher(suffix)
		if not match:
			continue
		try:
			number = match.group(1)
		except IndexError:
			number = ''
		return format_str.format(number)
	return suffix


class StandardVersion(_NamedTuple):
	numeric: str
	"""Main numeric part of the version, padding preserved: '1.2.3.01'."""
	suffix: str
	"""The remaining part of version - starting with a segment that has letters: 'alpha0-02'."""
	is_pre: bool = False
	"""Whether the version is detected as a pre-release - ``True`` when any part of suffix is an alpha/beta/RC."""
	sep_numeric: str = '.'
	"""Internal separator between segments in numeric part of version."""
	sep_parts: str = '-'
	"""Separator between numeric and suffix parts of version."""
	sep_suffix: str = '-'
	"""Internal separator between segments in suffix."""

	@classmethod
	def from_string(
		cls,
		version_str: str,
		sep_numeric='.', sep_parts='-', sep_suffix='-', convert_pre=True,
	) -> 'StandardVersion':
		parsed_version = _ParsedVersion.parse(version_str)
		number_parts = parsed_version.numbers
		suffix_parts = parsed_version.suffix

		suffix_converted = tuple(_convert_suffix_to_human_readable(x) for x in suffix_parts)
		is_pre = bool(
			suffix_converted and any(_pre_v_matcher(x) for x in suffix_converted)
		)

		numeric = sep_numeric.join(pad_i.format() for pad_i in number_parts)
		suffix = sep_suffix.join(
			suffix_converted if convert_pre else suffix_parts
		)

		return cls(
			numeric=numeric, suffix=suffix, is_pre=is_pre,
			sep_numeric=sep_numeric, sep_parts=sep_parts, sep_suffix=sep_suffix
		)

	@property
	def v_full(self) -> str:
		"""Full version with 'v' prefix - ready to be used as release tag: ``v1.2.3-alpha0``."""
		return f'v{self.full}'

	@property
	def full(self) -> str:
		"""Full assembled version without 'v' prefix: ``1.2.3-alpha0``."""
		suffix = self.suffix
		numeric = self.numeric
		return f'{numeric}{self.sep_parts}{suffix}' if suffix else numeric
