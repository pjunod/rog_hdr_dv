#!/usr/bin/python3
# SPDX-License-Identifier: LGPL-2.1-or-later
# Source-level helper controls only: no GI, window, decoder or playback.
import ast
from pathlib import Path
import sys
module = ast.parse(Path(sys.argv[1]).read_text())
helper = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "standard_destination_mapper")
namespace = {}
exec(compile(ast.Module(body=[helper], type_ignores=[]), str(sys.argv[1]), "exec"), namespace)
select = namespace["standard_destination_mapper"]
class Mapper:
    def __init__(self, properties, abi):
        self.properties, self.abi, self.writes = properties, abi, []
    def find_property(self, name):
        return name in self.properties
    def get_property(self, name):
        assert name == "destination-abi"
        return self.abi
    def set_property(self, name, value):
        self.writes.append((name, value))
assert select(None) is None
old = Mapper(set(), 0)
assert select(old) is None and not old.writes
partial = Mapper({"destination-abi"}, 1)
assert select(partial) is None and not partial.writes
wrong = Mapper({"destination-abi", "destination-kind"}, 2)
assert select(wrong) is None and not wrong.writes
current = Mapper({"destination-abi", "destination-kind"}, 1)
assert select(current) is current and current.writes == [("destination-kind", 1)]
print("RESULT checks=5 failures=0; source-level optional mapper startup only")
