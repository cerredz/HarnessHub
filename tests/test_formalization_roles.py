from __future__ import annotations

import unittest
import warnings

from harnessiq.formalization.roles import RoleLayer, RolePosition, RoleSpec


class RoleSpecValidationTests(unittest.TestCase):
    def test_valid_spec_constructs(self) -> None:
        spec = RoleSpec(name="Researcher", description="You are a researcher.")
        self.assertEqual(spec.name, "Researcher")
        self.assertEqual(spec.description, "You are a researcher.")
        self.assertEqual(spec.position, "top")
        self.assertEqual(spec.marker_text, "")
        self.assertTrue(spec.show_in_parameter_sections)

    def test_blank_name_raises(self) -> None:
        with self.assertRaises(ValueError, msg="name must not be blank"):
            RoleSpec(name="  ", description="desc")

    def test_blank_description_raises(self) -> None:
        with self.assertRaises(ValueError, msg="description must not be blank"):
            RoleSpec(name="Name", description="  ")

    def test_after_marker_with_empty_marker_text_raises(self) -> None:
        with self.assertRaises(ValueError, msg="marker_text required for after_marker"):
            RoleSpec(name="Name", description="desc", position="after_marker", marker_text="")

    def test_after_marker_with_whitespace_marker_text_raises(self) -> None:
        with self.assertRaises(ValueError):
            RoleSpec(name="Name", description="desc", position="after_marker", marker_text="   ")

    def test_after_marker_with_valid_marker_text(self) -> None:
        spec = RoleSpec(
            name="Name",
            description="desc",
            position="after_marker",
            marker_text="[IDENTITY]",
        )
        self.assertEqual(spec.marker_text, "[IDENTITY]")

    def test_spec_is_frozen(self) -> None:
        spec = RoleSpec(name="Name", description="desc")
        with self.assertRaises((AttributeError, TypeError)):
            spec.name = "Other"  # type: ignore[misc]

    def test_all_positions_accepted(self) -> None:
        positions: list[RolePosition] = ["top", "bottom", "after_marker"]
        for pos in positions:
            kwargs = {"name": "Name", "description": "desc", "position": pos}
            if pos == "after_marker":
                kwargs["marker_text"] = "[M]"
            RoleSpec(**kwargs)  # must not raise


class RoleLayerConstructionTests(unittest.TestCase):
    def test_empty_roles_raises(self) -> None:
        with self.assertRaises(ValueError):
            RoleLayer(roles=[])

    def test_single_role(self) -> None:
        layer = RoleLayer(roles=[RoleSpec(name="Engineer", description="You are an engineer.")])
        self.assertEqual(layer.layer_id, "RoleLayer")

    def test_multiple_roles(self) -> None:
        layer = RoleLayer(
            roles=[
                RoleSpec(name="Role A", description="Desc A"),
                RoleSpec(name="Role B", description="Desc B"),
            ]
        )
        desc = layer.describe()
        self.assertIn("Role A", desc.identity)
        self.assertIn("Role B", desc.identity)


class RoleLayerAugmentSystemPromptTests(unittest.TestCase):
    def _make_layer(self, *roles: RoleSpec) -> RoleLayer:
        return RoleLayer(roles=list(roles))

    def test_position_top_prepends(self) -> None:
        spec = RoleSpec(name="Eng", description="You are an engineer.", position="top")
        layer = self._make_layer(spec)
        result = layer.augment_system_prompt("Base prompt.")
        self.assertTrue(result.startswith("[ROLE: Eng]\nYou are an engineer."))
        self.assertIn("Base prompt.", result)

    def test_position_bottom_appends(self) -> None:
        spec = RoleSpec(name="Eng", description="You are an engineer.", position="bottom")
        layer = self._make_layer(spec)
        result = layer.augment_system_prompt("Base prompt.")
        self.assertTrue(result.endswith("[ROLE: Eng]\nYou are an engineer."))
        self.assertTrue(result.startswith("Base prompt."))

    def test_position_after_marker_inserts_after_marker(self) -> None:
        spec = RoleSpec(
            name="Eng",
            description="You are an engineer.",
            position="after_marker",
            marker_text="[TOOLS]",
        )
        layer = self._make_layer(spec)
        prompt = "Preamble.\n[TOOLS]\nMore content."
        result = layer.augment_system_prompt(prompt)
        marker_pos = result.index("[TOOLS]")
        role_pos = result.index("[ROLE: Eng]")
        self.assertGreater(role_pos, marker_pos)
        self.assertIn("More content.", result)

    def test_position_after_marker_falls_back_to_bottom_when_missing(self) -> None:
        spec = RoleSpec(
            name="Eng",
            description="You are an engineer.",
            position="after_marker",
            marker_text="[MISSING]",
        )
        layer = self._make_layer(spec)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = layer.augment_system_prompt("Base prompt.")
        self.assertTrue(any("not found" in str(w.message) for w in caught))
        self.assertTrue(result.endswith("[ROLE: Eng]\nYou are an engineer."))

    def test_multiple_roles_applied_in_order(self) -> None:
        spec_a = RoleSpec(name="A", description="Role A.", position="top")
        spec_b = RoleSpec(name="B", description="Role B.", position="bottom")
        layer = self._make_layer(spec_a, spec_b)
        result = layer.augment_system_prompt("Base.")
        self.assertTrue(result.startswith("[ROLE: A]"))
        self.assertTrue(result.endswith("[ROLE: B]\nRole B."))

    def test_empty_prompt_handled(self) -> None:
        spec = RoleSpec(name="Eng", description="You are an engineer.", position="top")
        layer = self._make_layer(spec)
        result = layer.augment_system_prompt("")
        self.assertIn("[ROLE: Eng]", result)


class RoleLayerParameterSectionsTests(unittest.TestCase):
    def test_visible_role_appears_in_sections(self) -> None:
        spec = RoleSpec(name="Eng", description="You are an engineer.", show_in_parameter_sections=True)
        layer = RoleLayer(roles=[spec])
        sections = layer.get_parameter_sections()
        titles = [s.title for s in sections]
        self.assertIn("Role: Eng", titles)

    def test_invisible_role_excluded_from_sections(self) -> None:
        spec = RoleSpec(name="Eng", description="You are an engineer.", show_in_parameter_sections=False)
        layer = RoleLayer(roles=[spec])
        sections = layer.get_parameter_sections()
        titles = [s.title for s in sections]
        self.assertNotIn("Role: Eng", titles)

    def test_mixed_visibility(self) -> None:
        spec_a = RoleSpec(name="A", description="Desc A", show_in_parameter_sections=True)
        spec_b = RoleSpec(name="B", description="Desc B", show_in_parameter_sections=False)
        layer = RoleLayer(roles=[spec_a, spec_b])
        sections = layer.get_parameter_sections()
        titles = [s.title for s in sections]
        self.assertIn("Role: A", titles)
        self.assertNotIn("Role: B", titles)

    def test_section_content_matches_description(self) -> None:
        spec = RoleSpec(name="Eng", description="You are an engineer.")
        layer = RoleLayer(roles=[spec])
        sections = layer.get_parameter_sections()
        role_section = next(s for s in sections if s.title == "Role: Eng")
        self.assertEqual(role_section.content, "You are an engineer.")


class RoleLayerDescribeTests(unittest.TestCase):
    def test_describe_renders_correctly(self) -> None:
        spec = RoleSpec(name="Senior Engineer", description="You are a senior engineer.")
        layer = RoleLayer(roles=[spec])
        desc = layer.describe()
        self.assertEqual(desc.layer_id, "RoleLayer")
        self.assertIn("Senior Engineer", desc.identity)
        self.assertIn("Senior Engineer", desc.contract)
        self.assertEqual(len(desc.rules), 1)
        rule = desc.rules[0]
        self.assertEqual(rule.enforced_at, "augment_system_prompt")
        self.assertEqual(rule.enforcement_type, "inject")
        self.assertIn("ROLE-INJECT-SENIOR-ENGINEER", rule.rule_id)

    def test_describe_configuration(self) -> None:
        spec = RoleSpec(name="Eng", description="desc", position="bottom")
        layer = RoleLayer(roles=[spec])
        config = layer.describe().configuration
        self.assertEqual(config["role_count"], 1)
        self.assertEqual(config["roles"][0]["position"], "bottom")


if __name__ == "__main__":
    unittest.main()
