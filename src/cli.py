#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:Mod: cli

:Synopsis:
    Metapype Command Line Interface

    This module implements a client of the Metapype EML library.
    Although it can be used to create EML documents, its primary
    purpose was to build a rapid prototype of a metapype client.

:Author:
    costa

:Created:
    7/12/18
"""
import json

import daiquiri
from input_functions import read_int_ranged, read_text, yes_no, read_text_with_choices

from metapype.eml2_1_1.exceptions import MetapypeRuleError
from metapype.eml2_1_1 import export
from metapype.eml2_1_1 import evaluate
from metapype.eml2_1_1 import names
from metapype.eml2_1_1 import rule
from metapype.eml2_1_1 import validate
from metapype.model.node import Node
from metapype.model import io


logger = daiquiri.getLogger('harness: ' + __name__)


main_menu_text = '''
Metapype CLI -- Main Menu

1: Create a new node
2: View node as JSON
3: View node as XML
4: Edit node
5: Load node
6: Save node
7: Exit program

Enter your command: '''


def edit_attributes(node=None, node_rule=None):
    if node is not None and \
       node_rule is not None and \
       len(node_rule.attributes.keys()) > 0:
        print(f"Please supply attribute values for the {node.name} node. (*) indicates required")
        for attribute_name in node_rule.attributes:
            prompt = f"{attribute_name}"
            required = node_rule.is_required_attribute(attribute_name)
            if required:
                prompt = prompt + " (*)"
            prompt = prompt + ": "
            values = node_rule.allowed_attribute_values(attribute_name)
            while True:
                is_valid_value = True
                if len(values) > 0:
                    attribute_value = read_text_with_choices(prompt, required, values)
                else:
                    attribute_value = read_text(prompt)
                if len(values) > 0 and attribute_value not in values:
                    if not required and attribute_value == '':
                        is_valid_value = True
                    else:
                        is_valid_value = False
                if required and attribute_value == '':
                    is_valid_value = False
                if is_valid_value:
                    break
            if attribute_value != '':
                node.add_attribute(attribute_name, attribute_value)


def edit_content(node, node_rule):
    required = False
    asterisk = ""
    content_rules = node_rule.content_rules
    if "emptyContent" in content_rules:
        return
    values = node_rule.content_enum
    if "nonEmptyContent" in content_rules or len(values) > 0:
        required = True
        asterisk = " (*)"
    prompt = f"Content for {node.name}{asterisk} : "
    if len(values) > 0:
        content_value = read_text_with_choices(prompt, required, values)
    else:
        content_value = read_text(prompt)
    if required and content_value == '':
        content_value = edit_content(node, node_rule)
    node.content = content_value
    return content_value


def edit_children(node, node_rule):
    for child_list in node_rule.children:
        node_names = rule.Rule.child_list_node_names(child_list)
        has_choices = len(node_names) > 1
        min_occurences = int(rule.Rule.child_list_min_occurrences(child_list))
        max_occurences = rule.Rule.child_list_max_occurrences(child_list)
        child_count = 0
        if max_occurences is not None:
            try:
                max_occurences = int(max_occurences)
            except ValueError:
                raise Exception(f"max occurences must be integer or None: {max_occurences}")

        while True:
            if max_occurences is not None and child_count >= max_occurences:
                break
            else:
                print(f"{node.name} may have the following child nodes: {node_names}")
                if child_count < min_occurences:
                    do_another = True
                else:
                    word = "a"
                    if child_count > 0:
                        word = "another"
                    do_another = yes_no(f"Create {word} child node for {node.name}?")

                if do_another:
                    required = True
                    if has_choices:
                        child_name = read_text_with_choices(f"Choose a child for {node.name}", required, node_names)
                    else:
                        child_name = node_names[0]
                    child_node = create_node(child_name)
                    node.add_child(child_node)
                    child_count = child_count + 1
                else:
                    break


def create_node(node_name=''):
    node = None
    node_names = rule.node_names()
    required = True
    if node_name=='':
        node_name = read_text_with_choices(
            "Which type of EML node would you like to work on?: ",
            required,
            node_names)
    if node_name in rule.node_mappings:
        node = Node(node_name)
        node_rule = rule.get_rule(node_name)
        print(f"Building a {node_name} node using rule {node_rule.name}.")
        edit_attributes(node, node_rule)
        edit_content(node, node_rule)
        edit_children(node, node_rule)
    else:
        print(f"Sorry, I don't know about a {node_name} node.")
    return node


def view_node_json(node:Node=None):
    if node is None:
        print("There is currently no node to view")
    json_str = io.to_json(node)
    print(json_str)


def view_node_xml(node:Node=None):
    if node is None:
        print("There is currenlty no node to view")
    xml_str = export.to_xml(node)
    print(xml_str)


def save_node(node:Node=None):
    if node is not None:
        required = True
        file_extension = read_text_with_choices("Format as", required, ['json', 'xml'])
        file_name_default = f"{node.name}-{node.id}.{file_extension}"
        file_name = read_text(f"Enter a filename or press return for the default [{file_name_default}]: ")
        if file_name == '':
            file_name = file_name_default

        if file_extension == 'json':
            metadata = io.to_json(node)
        else:
            metadata = export.to_xml(node)

        with open(file_name, "w") as fh:
            fh.write(metadata)

        print(f"Node {node.name} saved to file {file_name}")


def main_menu():
    node = None
    while (True):
        choice = read_int_ranged(main_menu_text, 1, 7)
        if choice == 1:
            node = create_node()
        elif choice == 2:
            view_node_json(node)
        elif choice == 3:
            view_node_xml(node)
        elif choice == 4:
            print("Let's edit this node!")
        elif choice == 5:
            print("Let's load a node!")
        elif choice == 6:
            save_node(node)
        elif choice == 7:
            print("Bye Bye!")
            return


def main():
    print('\nWelcome to the Metapype Command Line Interface')
    main_menu()
    return


if __name__ == "__main__":
    main()
