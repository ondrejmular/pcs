"""
Module contains list of functions that should be usefull for validation.
Example of use (how things play together):
    >>> option_dict = {"some_option": "A"}
    >>> validators = [
    ...     is_required("name"),
    ...     value_in("some_option", ["B", "C"])
    ... ]
    >>> report_list = run_collection_of_option_validators(
    ...     option_dict,
    ...     validators
    ... )
    >>> for report in report_list:
    ...     print(report)
    ...
    ...
    ERROR REQUIRED_OPTION_IS_MISSING: {
        'option_type': 'option',
        'option_names': ['name']
    }
    ERROR INVALID_OPTION_VALUE: {
        'option_name': 'some_option',
        'option_value': 'A',
        'allowed_values': ['B', 'C']
    }

Sometimes we need to validate the normalized value but in report we need the
original value. For this purposes is ValuePair and helpers like values_to_pairs
and pairs_to_values.

TODO provide parameters to provide forceable error/warning for functions that
     does not support it
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from collections import namedtuple

from pcs.lib import reports

class ValuePair(namedtuple("ValuePair", "original normalized")):
    """
    Storage for the original value and its normalized form
    """

def values_to_pairs(option_dict, normalize):
    """
    Return a dict derived from option_dict where every value is instance of
    ValuePair.

    dict option_dict contains values that should be paired with the normalized
        form
    callable normalize should take key and value and return normalized form.
        Function option_value_normalization can be good base for create such
        callable.
    """
    option_dict_with_pairs = {}
    for key, value in option_dict.items():
        if not isinstance(value, ValuePair):
            value = ValuePair(
                original=value,
                normalized=normalize(key, value),
            )
        option_dict_with_pairs[key] = value
    return option_dict_with_pairs

def pairs_to_values(option_dict):
    """
    Take a dict which has OptionValuePairs as its values and return dict with
    normalized forms as its values. It is reverse function to
    values_to_pairs.

    dict option_dict contains OptionValuePairs as its values
    """
    raw_option_dict = {}
    for key, value in option_dict.items():
        if isinstance(value, ValuePair):
            value = value.normalized
        raw_option_dict[key] = value
    return raw_option_dict

def option_value_normalization(normalization_map):
    """
    Return function that takes key and value and return the normalized form.

    dict normalization_map has on each key function that takes value and return
        its normalized form.
    """
    def normalize(key, value):
        return(
            value if key not in normalization_map
            else normalization_map[key](value)
        )
    return normalize

def is_required(option_name, option_type="option"):
    """
    Return a the function that takes option_dict and returns report list
    (with REQUIRED_OPTION_IS_MISSING when option_dict does not contain
    option_name).

    string option_name is name of option of option_dict that will be tested
    string option_type describes type of option for reporting purposes
    """
    def validate(option_dict):
        if option_name not in option_dict:
            return [reports.required_option_is_missing(
                [option_name],
                option_type,
            )]
        return []
    return validate

def value_in(option_name, allowed_values):
    """
    Return a the function that takes option_dict and returns report list
    (with INVALID_OPTION_VALUE when option_name is not in allowed_values).

    string option_name is name of option of option_dict that will be tested
    list allowed_values contains all possibilities of option value
    """
    def validate(option_dict):
        if option_name not in option_dict:
            return []

        value = option_dict[option_name]
        if not isinstance(value, ValuePair):
            value = ValuePair(value, value)

        if(value.normalized not in allowed_values):
            return [reports.invalid_option_value(
                option_name,
                value.original,
                allowed_values,
            )]
        return []
    return validate

def mutually_exclusive(mutually_exclusive_names, option_type="option"):
    """
    Return a list with report MUTUALLY_EXCLUSIVE_OPTIONS when in option_dict
    appears more than one of mutually_exclusive_names.

    list|set mutually_exclusive_names contains option names that cannot appear
        together
    string option_type describes type of option for reporting purposes
    """
    def validate(option_dict):
        names_that_appeared = set.intersection(
            set(option_dict.keys()),
            set(mutually_exclusive_names)
        )
        if len(names_that_appeared) > 1:
            return [reports.mutually_exclusive_options(
                sorted(list(names_that_appeared)),
                option_type,
            )]
        return []
    return validate

def run_collection_of_option_validators(option_dict, validator_list):
    """
    Return a list with reports (ReportItems) about problems inside items of
    option_dict.

    dict option_dict is source of values to validate according to specification
    list validator_list contains callables that takes option_dict and returns
        list of reports
    """
    report_list = []
    for validate in validator_list:
        report_list.extend(validate(option_dict))
    return report_list

def names_in(
    allowed_name_list, name_list, option_type="option",
    code_to_allow_extra_names=None, allow_extra_names=False
):
    """
    Return a list with report INVALID_OPTION when in name_list is a name that is
    not in allowed_name_list.

    list allowed_name_list contains names which are valid
    list name_list contains names for validation
    string option_type describes type of option for reporting purposes
    string code_to_allow_extra_names is code for forcing invalid names. If it is
        empty report INVALID_OPTION is non-forceable error. If it is not empty
        report INVALID_OPTION is forceable error or warning.
    bool allow_extra_names is flag that complements code_to_allow_extra_names
        and determines wheter is report INVALID_OPTION forceable error or
        warning.
    """
    invalid_names = set(name_list) - set(allowed_name_list)
    if not invalid_names:
        return []

    return [reports.get_creator(code_to_allow_extra_names, allow_extra_names)(
        reports.invalid_option,
        sorted(invalid_names),
        sorted(allowed_name_list),
        option_type,
    )]
