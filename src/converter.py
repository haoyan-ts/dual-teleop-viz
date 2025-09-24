#!/usr/bin/env python3
"""
URDF to XACRO Converter

This module provides functionality to convert URDF (Unified Robot Description Format)
files to XACRO (XML Macros) format with parameterization and macro definitions.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Literal
from dataclasses import dataclass
import tyro


@dataclass
class LinkInfo:
    """Information about a URDF link"""

    name: str
    element: ET.Element
    mass: Optional[float] = None
    inertia: Optional[Dict[str, float]] = None
    visual_mesh: Optional[str] = None
    collision_mesh: Optional[str] = None


@dataclass
class JointInfo:
    """Information about a URDF joint"""

    name: str
    element: ET.Element
    joint_type: str
    parent: str
    child: str
    axis: Optional[Tuple[float, float, float]] = None
    limits: Optional[Dict[str, float]] = None


class URDFToXacroConverter:
    """
    Converts URDF files to XACRO format with parameterization and macro generation
    """

    def __init__(self):
        self.links: Dict[str, LinkInfo] = {}
        self.joints: Dict[str, JointInfo] = {}
        self.materials: Dict[str, ET.Element] = {}
        self.properties: Dict[str, str] = {}
        self.macros: List[ET.Element] = []

    def parse_urdf(self, urdf_content: str) -> ET.Element:
        """
        Parse URDF XML content and extract components

        Args:
            urdf_content: String content of the URDF file

        Returns:
            Root element of the parsed XML
        """
        try:
            root = ET.fromstring(urdf_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid URDF XML: {e}")

        if root.tag != "robot":
            raise ValueError("URDF file must have 'robot' as root element")

        # Extract links
        for link in root.findall("link"):
            link_info = self._extract_link_info(link)
            self.links[link_info.name] = link_info

        # Extract joints
        for joint in root.findall("joint"):
            joint_info = self._extract_joint_info(joint)
            self.joints[joint_info.name] = joint_info

        # Extract materials
        for material in root.findall("material"):
            name = material.get("name")
            if name:
                self.materials[name] = material

        return root

    def _extract_link_info(self, link_element: ET.Element) -> LinkInfo:
        """Extract information from a link element"""
        name = link_element.get("name", "")

        # Extract mass
        mass = None
        inertial = link_element.find("inertial")
        if inertial is not None:
            mass_elem = inertial.find("mass")
            if mass_elem is not None:
                try:
                    mass = float(mass_elem.get("value", 0))
                except ValueError:
                    mass = None

        # Extract inertia
        inertia = None
        if inertial is not None:
            inertia_elem = inertial.find("inertia")
            if inertia_elem is not None:
                inertia = {
                    "ixx": float(inertia_elem.get("ixx", 0)),
                    "ixy": float(inertia_elem.get("ixy", 0)),
                    "ixz": float(inertia_elem.get("ixz", 0)),
                    "iyy": float(inertia_elem.get("iyy", 0)),
                    "iyz": float(inertia_elem.get("iyz", 0)),
                    "izz": float(inertia_elem.get("izz", 0)),
                }

        # Extract mesh filenames
        visual_mesh = None
        collision_mesh = None

        visual = link_element.find("visual")
        if visual is not None:
            geometry = visual.find("geometry")
            if geometry is not None:
                mesh = geometry.find("mesh")
                if mesh is not None:
                    visual_mesh = mesh.get("filename")

        collision = link_element.find("collision")
        if collision is not None:
            geometry = collision.find("geometry")
            if geometry is not None:
                mesh = geometry.find("mesh")
                if mesh is not None:
                    collision_mesh = mesh.get("filename")

        return LinkInfo(
            name=name,
            element=link_element,
            mass=mass,
            inertia=inertia,
            visual_mesh=visual_mesh,
            collision_mesh=collision_mesh,
        )

    def _extract_joint_info(self, joint_element: ET.Element) -> JointInfo:
        """Extract information from a joint element"""
        name = joint_element.get("name", "")
        joint_type = joint_element.get("type", "")

        # Extract parent and child
        parent_elem = joint_element.find("parent")
        child_elem = joint_element.find("child")
        parent = parent_elem.get("link", "") if parent_elem is not None else ""
        child = child_elem.get("link", "") if child_elem is not None else ""

        # Extract axis
        axis = None
        axis_elem = joint_element.find("axis")
        if axis_elem is not None:
            xyz = axis_elem.get("xyz", "0 0 0")
            try:
                axis_values = [float(x) for x in xyz.split()]
                if len(axis_values) == 3:
                    axis = (axis_values[0], axis_values[1], axis_values[2])
            except ValueError:
                axis = None

        # Extract limits
        limits = None
        limit_elem = joint_element.find("limit")
        if limit_elem is not None:
            limits = {}
            for attr in ["lower", "upper", "effort", "velocity"]:
                value = limit_elem.get(attr)
                if value is not None:
                    try:
                        limits[attr] = float(value)
                    except ValueError:
                        pass

        return JointInfo(
            name=name,
            element=joint_element,
            joint_type=joint_type,
            parent=parent,
            child=child,
            axis=axis,
            limits=limits,
        )

    def _identify_common_patterns(self) -> Dict[str, List[LinkInfo]]:
        """
        Identify common patterns in links that can be parameterized

        Returns:
            Dictionary mapping pattern names to lists of links matching that pattern
        """
        patterns = {}

        # Group links by similar mesh patterns
        mesh_patterns = {}
        for link in self.links.values():
            if link.visual_mesh:
                # Extract pattern from mesh filename
                mesh_base = self._extract_mesh_pattern(link.visual_mesh)
                if mesh_base not in mesh_patterns:
                    mesh_patterns[mesh_base] = []
                mesh_patterns[mesh_base].append(link)

        # Only keep patterns with multiple links
        for pattern, links in mesh_patterns.items():
            if len(links) > 1:
                patterns[f"mesh_{pattern}"] = links

        return patterns

    def _extract_mesh_pattern(self, mesh_filename: str) -> str:
        """Extract base pattern from mesh filename"""
        if not mesh_filename:
            return "unknown"

        # Extract package and base name
        if "package://" in mesh_filename:
            parts = mesh_filename.split("/")
            if len(parts) >= 3:
                package = parts[1]
                filename = parts[-1]
                # Remove file extension
                base_name = filename.rsplit(".", 1)[0]
                return f"{package}_{base_name}"

        return "default"

    def _create_properties(self):
        """Create XACRO properties for common values"""
        # Create properties for common dimensions, masses, etc.
        masses = [link.mass for link in self.links.values() if link.mass is not None]
        if masses:
            avg_mass = sum(masses) / len(masses)
            self.properties["default_mass"] = str(avg_mass)

        # Add common material properties
        self.properties["default_color"] = "0.8 0.8 0.8 1.0"
        self.properties["package_name"] = "robot_description"

        # Add prefix and base link properties
        self.properties["prefix"] = ""
        self.properties["base_link_name"] = "base_link"

    def generate_xacro(self, robot_name: str, original_root: ET.Element) -> str:
        """
        Generate XACRO content from parsed URDF

        Args:
            robot_name: Name of the robot
            original_root: Original URDF root element

        Returns:
            XACRO content as string
        """
        # Create root element with XACRO namespace
        xacro_root = ET.Element("robot")
        xacro_root.set("name", robot_name)
        xacro_root.set("xmlns:xacro", "http://www.ros.org/wiki/xacro")

        # Add common properties
        self._create_properties()
        for prop_name, prop_value in self.properties.items():
            prop_elem = ET.SubElement(xacro_root, "xacro:property")
            prop_elem.set("name", prop_name)
            prop_elem.set("value", prop_value)

        # Add materials if they exist
        for material in self.materials.values():
            xacro_root.append(material)

        # Create main robot macro with prefix and base_link_name parameters
        main_macro = self._create_main_robot_macro(robot_name, original_root)
        xacro_root.append(main_macro)

        # Create macro call for the main robot
        macro_call = ET.SubElement(xacro_root, f"xacro:{robot_name}")
        macro_call.set("prefix", "${prefix}")
        macro_call.set("base_link_name", "${base_link_name}")

        # Convert to string with proper formatting
        return self._format_xacro_xml(xacro_root)

    def _create_main_robot_macro(
        self, robot_name: str, original_root: ET.Element
    ) -> ET.Element:
        """
        Create the main robot macro with prefix and base_link_name parameters

        Args:
            robot_name: Name of the robot
            original_root: Original URDF root element

        Returns:
            Main robot macro element
        """
        macro_elem = ET.Element("xacro:macro")
        macro_elem.set("name", f"{robot_name}")
        macro_elem.set("params", "prefix base_link_name")

        # Identify patterns for link macro creation
        patterns = self._identify_common_patterns()

        # Create macros for repeated patterns within the main macro
        for pattern_name, links in patterns.items():
            sub_macro = self._create_link_macro(pattern_name, links[0])
            if sub_macro is not None:
                macro_elem.append(sub_macro)

        # Process all links with prefix support
        processed_links = set()

        # Use macros for pattern-matched links
        for pattern_name, links in patterns.items():
            for link in links:
                if link.name not in processed_links:
                    macro_call = self._create_macro_call(
                        pattern_name, link, use_prefix=True
                    )
                    if macro_call is not None:
                        macro_elem.append(macro_call)
                    processed_links.add(link.name)

        # Add remaining links with prefix support
        for link in self.links.values():
            if link.name not in processed_links:
                prefixed_link = self._create_prefixed_link(link)
                macro_elem.append(prefixed_link)

        # Add all joints with prefix support
        for joint in self.joints.values():
            prefixed_joint = self._create_prefixed_joint(joint)
            macro_elem.append(prefixed_joint)

        return macro_elem

    def _create_link_macro(
        self, pattern_name: str, template_link: LinkInfo
    ) -> Optional[ET.Element]:
        """
        Create a macro definition for a link pattern

        Args:
            pattern_name: Name of the pattern
            template_link: Template link to base macro on

        Returns:
            Macro element or None if macro cannot be created
        """
        if not template_link.element:
            return None

        macro_elem = ET.Element("xacro:macro")
        macro_elem.set("name", f"{pattern_name}_link")

        # Add parameters
        params = ["prefix", "link_name", "mesh_file"]
        if template_link.mass is not None:
            params.append("mass")
        params_str = " ".join(params)
        macro_elem.set("params", params_str)

        # Create parameterized link
        link_elem = ET.SubElement(macro_elem, "link")
        link_elem.set("name", "${prefix}${link_name}")

        # Copy structure from template but parameterize values
        self._parameterize_link_element(template_link.element, link_elem)

        return macro_elem

    def _parameterize_link_element(
        self, source_elem: ET.Element, target_elem: ET.Element
    ):
        """Parameterize a link element for macro use"""
        for child in source_elem:
            new_child = ET.SubElement(target_elem, child.tag)

            # Copy attributes, parameterizing where appropriate
            for attr_name, attr_value in child.attrib.items():
                if attr_name == "filename" and "package://" in attr_value:
                    new_child.set(attr_name, "${mesh_file}")
                elif attr_name == "value" and child.tag == "mass":
                    new_child.set(attr_name, "${mass}")
                else:
                    new_child.set(attr_name, attr_value)

            # Recursively process children
            if len(child) > 0:
                self._parameterize_link_element(child, new_child)
            elif child.text and child.text.strip():
                new_child.text = child.text

    def _create_macro_call(
        self, pattern_name: str, link: LinkInfo, use_prefix: bool = False
    ) -> Optional[ET.Element]:
        """Create a macro call for a specific link"""
        call_elem = ET.Element(f"xacro:{pattern_name}_link")

        if use_prefix:
            call_elem.set("prefix", "${prefix}")
            # Handle base link name replacement
            if link.name == "base_link":
                call_elem.set("link_name", "${base_link_name}")
            else:
                call_elem.set("link_name", link.name)
        else:
            call_elem.set("link_name", link.name)

        if link.visual_mesh:
            call_elem.set("mesh_file", link.visual_mesh)
        if link.mass is not None:
            call_elem.set("mass", str(link.mass))

        return call_elem

    def _create_prefixed_link(self, link: LinkInfo) -> ET.Element:
        """
        Create a link element with prefix support

        Args:
            link: Original link information

        Returns:
            Link element with prefixed name
        """
        link_elem = ET.Element("link")

        # Handle base link name replacement
        if link.name == "base_link":
            link_elem.set("name", "${prefix}${base_link_name}")
        else:
            link_elem.set("name", f"${{prefix}}{link.name}")

        # Copy all child elements from original link
        for child in link.element:
            self._copy_element_with_parameterization(child, link_elem)

        return link_elem

    def _create_prefixed_joint(self, joint: JointInfo) -> ET.Element:
        """
        Create a joint element with prefix support for joint name, parent and child links

        Args:
            joint: Original joint information

        Returns:
            Joint element with prefixed joint name and link references
        """
        joint_elem = ET.Element("joint")

        # Copy all attributes from original joint with prefix handling
        for attr_name, attr_value in joint.element.attrib.items():
            if attr_name == "name":
                # Add prefix to joint name
                joint_elem.set(attr_name, f"${{prefix}}{attr_value}")
            else:
                joint_elem.set(attr_name, attr_value)

        # Copy and modify child elements
        for child in joint.element:
            new_child = ET.SubElement(joint_elem, child.tag)

            # Copy attributes with prefix handling for parent/child links
            for attr_name, attr_value in child.attrib.items():
                if attr_name == "link":
                    if attr_value == "base_link":
                        new_child.set(attr_name, "${prefix}${base_link_name}")
                    else:
                        new_child.set(attr_name, f"${{prefix}}{attr_value}")
                else:
                    new_child.set(attr_name, attr_value)

            # Copy child elements recursively
            if len(child) > 0:
                self._copy_element_with_parameterization(child, new_child)
            elif child.text and child.text.strip():
                new_child.text = child.text

        return joint_elem

    def _copy_element_with_parameterization(
        self, source: ET.Element, target: ET.Element
    ):
        """
        Copy element structure with parameterization for mesh files and mass values

        Args:
            source: Source element to copy from
            target: Target element to copy to
        """
        for child in source:
            new_child = ET.SubElement(target, child.tag)

            # Copy attributes, parameterizing where appropriate
            for attr_name, attr_value in child.attrib.items():
                if attr_name == "filename" and "package://" in attr_value:
                    # Keep mesh files as-is, or could parameterize if needed
                    new_child.set(attr_name, attr_value)
                elif attr_name == "value" and child.tag == "mass":
                    # Could parameterize mass values if needed
                    new_child.set(attr_name, attr_value)
                else:
                    new_child.set(attr_name, attr_value)

            # Recursively process children
            if len(child) > 0:
                self._copy_element_with_parameterization(child, new_child)
            elif child.text and child.text.strip():
                new_child.text = child.text

    def _format_xacro_xml(self, root: ET.Element) -> str:
        """Format XML with proper indentation and XACRO header"""
        # Add XML declaration and pretty formatting
        xml_str = ET.tostring(root, encoding="unicode")

        # Parse with minidom for pretty printing
        from xml.dom import minidom

        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")

        # Remove empty lines and fix formatting
        lines = [line for line in pretty_xml.split("\n") if line.strip()]

        # Replace the first line with proper XML declaration
        if lines and lines[0].startswith("<?xml"):
            lines[0] = '<?xml version="1.0"?>'

        return "\n".join(lines)

    def convert_file(
        self, input_file: str, output_file: str, robot_name: Optional[str] = None
    ) -> None:
        """
        Convert a URDF file to XACRO format

        Args:
            input_file: Path to input URDF file
            output_file: Path to output XACRO file
            robot_name: Name for the robot (extracted from URDF if not provided)
        """
        # Read URDF file
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                urdf_content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"URDF file not found: {input_file}")
        except Exception as e:
            raise IOError(f"Error reading URDF file: {e}")

        # Parse URDF
        root = self.parse_urdf(urdf_content)

        # Extract robot name if not provided
        if robot_name is None:
            robot_name = root.get("name", "robot")

        # Generate XACRO
        xacro_content = self.generate_xacro(robot_name, root)

        # Write XACRO file
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(xacro_content)
        except Exception as e:
            raise IOError(f"Error writing XACRO file: {e}")

    def convert_string(
        self, urdf_content: str, robot_name: Optional[str] = None
    ) -> str:
        """
        Convert URDF content string to XACRO format

        Args:
            urdf_content: URDF content as string
            robot_name: Name for the robot (extracted from URDF if not provided)

        Returns:
            XACRO content as string
        """
        # Parse URDF
        root = self.parse_urdf(urdf_content)

        # Extract robot name if not provided
        if robot_name is None:
            robot_name = root.get("name", "robot")

        # Generate and return XACRO
        return self.generate_xacro(robot_name, root)


class XacroToURDFConverter:
    """
    Converts XACRO files to URDF format by expanding macros and resolving properties
    """

    def __init__(self):
        self.properties: Dict[str, str] = {}
        self.macros: Dict[str, ET.Element] = {}
        self.includes: List[str] = []

    def parse_xacro(self, xacro_content: str, base_path: str = "") -> ET.Element:
        """
        Parse XACRO XML content and process XACRO-specific elements

        Args:
            xacro_content: String content of the XACRO file
            base_path: Base path for resolving includes

        Returns:
            Root element of the processed XML
        """
        try:
            root = ET.fromstring(xacro_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XACRO XML: {e}")

        if root.tag != "robot":
            raise ValueError("XACRO file must have 'robot' as root element")

        # First pass: collect properties, macros, and includes
        self._collect_xacro_elements(root, base_path)

        # Second pass: expand macros and substitute properties
        expanded_root = self._expand_xacro_elements(root)

        return expanded_root

    def _collect_xacro_elements(self, element: ET.Element, base_path: str = ""):
        """Collect XACRO properties, macros, and includes"""
        elements_to_remove = []

        for child in list(element):
            # Handle namespace-aware tag checking
            local_tag = self._get_local_tag(child.tag)

            if local_tag == "property" and self._is_xacro_element(child.tag):
                # Collect property
                name = child.get("name")
                value = child.get("value", "")
                if name:
                    # Resolve any property references in the value
                    value = self._resolve_properties(value)
                    self.properties[name] = value
                elements_to_remove.append(child)

            elif local_tag == "macro" and self._is_xacro_element(child.tag):
                # Collect macro
                name = child.get("name")
                if name:
                    self.macros[name] = child
                elements_to_remove.append(child)

            elif local_tag == "include" and self._is_xacro_element(child.tag):
                # Handle include (simplified - just record for now)
                filename = child.get("filename", "")
                if filename:
                    self.includes.append(filename)
                elements_to_remove.append(child)

            else:
                # Recursively process child elements
                self._collect_xacro_elements(child, base_path)

        # Remove processed XACRO elements
        for elem in elements_to_remove:
            element.remove(elem)

    def _get_local_tag(self, tag: str) -> str:
        """Get the local part of a namespaced tag"""
        if "}" in tag:
            # Handle {namespace}localname format
            return tag.split("}")[-1]
        elif ":" in tag:
            # Handle prefix:localname format
            return tag.split(":")[-1]
        return tag

    def _is_xacro_element(self, tag: str) -> bool:
        """Check if a tag is a XACRO element (by namespace URI or prefix)"""
        # Check for XACRO namespace URI
        if "}" in tag and "xacro" in tag:
            return True
        # Check for xacro prefix or any namespace prefix ending with property/macro/include
        if ":" in tag:
            prefix, local = tag.split(":", 1)
            return local in ["property", "macro", "include"] or prefix == "xacro"
        return False

    def _resolve_properties(self, text: str) -> str:
        """Resolve property references in text using ${property_name} syntax"""
        import re

        def replace_property(match) -> str:
            prop_name = match.group(1)
            return self.properties.get(prop_name, match.group(0)) or match.group(0)

        # Replace ${property_name} patterns
        result = re.sub(r"\$\{([^}]+)\}", replace_property, text)
        return result

    def _expand_xacro_elements(self, element: ET.Element) -> ET.Element:
        """Expand XACRO elements and substitute properties"""
        # Create a new element to avoid modifying during iteration
        new_element = ET.Element(element.tag)

        # Copy attributes with property substitution
        for attr_name, attr_value in element.attrib.items():
            if attr_name.startswith("xmlns"):
                # Skip XACRO namespace declarations in output
                if "xacro" not in attr_value:
                    new_element.set(attr_name, attr_value)
            else:
                resolved_value = self._resolve_properties(attr_value)
                new_element.set(attr_name, resolved_value)

        # Process children
        for child in element:
            if self._is_macro_call(child):
                # Expand macro call
                expanded_elements = self._expand_macro_call(child)
                for expanded in expanded_elements:
                    new_element.append(expanded)
            elif child.tag.startswith("xacro:") and not self._is_macro_call(child):
                # Skip other XACRO-specific elements that weren't handled in collection
                continue
            else:
                # Recursively process regular elements
                expanded_child = self._expand_xacro_elements(child)
                new_element.append(expanded_child)

        # Handle text content
        if element.text and element.text.strip():
            new_element.text = self._resolve_properties(element.text)
        if element.tail and element.tail.strip():
            new_element.tail = self._resolve_properties(element.tail)

        return new_element

    def _is_macro_call(self, element: ET.Element) -> bool:
        """Check if element is a macro call"""
        local_tag = self._get_local_tag(element.tag)

        # Check if it's a known macro
        if local_tag in self.macros:
            return True

        # Check if the full tag (with namespace) matches a macro
        if element.tag in self.macros:
            return True

        # Check for xacro namespace prefix
        if self._is_xacro_element(element.tag) and local_tag in self.macros:
            return True

        return False

    def _expand_macro_call(self, call_element: ET.Element) -> List[ET.Element]:
        """Expand a macro call with parameter substitution"""
        # Determine macro name
        local_tag = self._get_local_tag(call_element.tag)
        macro_name = local_tag

        # Try to find the macro by local name or full tag
        macro_def = None
        if macro_name in self.macros:
            macro_def = self.macros[macro_name]
        elif call_element.tag in self.macros:
            macro_def = self.macros[call_element.tag]

        if macro_def is None:
            # Return empty list if macro not found
            return []

        # Get macro parameters
        params_attr = macro_def.get("params", "")
        param_names = [p.strip() for p in params_attr.split() if p.strip()]

        # Create parameter mapping from call attributes
        param_values = {}
        for attr_name, attr_value in call_element.attrib.items():
            if attr_name in param_names:
                param_values[attr_name] = self._resolve_properties(attr_value)

        # Expand macro content
        expanded_elements = []
        for macro_child in macro_def:
            expanded = self._expand_macro_content(macro_child, param_values)
            if expanded is not None:
                expanded_elements.append(expanded)

        return expanded_elements

    def _expand_macro_content(
        self, element: ET.Element, params: Dict[str, str]
    ) -> Optional[ET.Element]:
        """Expand macro content with parameter substitution"""
        # Create new element
        new_element = ET.Element(element.tag)

        # Copy and substitute attributes
        for attr_name, attr_value in element.attrib.items():
            substituted_value = self._substitute_parameters(attr_value, params)
            substituted_value = self._resolve_properties(substituted_value)
            new_element.set(attr_name, substituted_value)

        # Process children
        for child in element:
            expanded_child = self._expand_macro_content(child, params)
            if expanded_child is not None:
                new_element.append(expanded_child)

        # Handle text content
        if element.text and element.text.strip():
            substituted_text = self._substitute_parameters(element.text, params)
            substituted_text = self._resolve_properties(substituted_text)
            new_element.text = substituted_text

        return new_element

    def _substitute_parameters(self, text: str, params: Dict[str, str]) -> str:
        """Substitute macro parameters in text using ${param_name} syntax"""
        import re

        def replace_param(match) -> str:
            param_name = match.group(1)
            return params.get(param_name, match.group(0)) or match.group(0)

        # Replace ${param_name} patterns
        result = re.sub(r"\$\{([^}]+)\}", replace_param, text)
        return result

    def generate_urdf(self, robot_name: str, processed_root: ET.Element) -> str:
        """
        Generate clean URDF content from processed XACRO

        Args:
            robot_name: Name of the robot
            processed_root: Processed XACRO root element

        Returns:
            URDF content as string
        """
        # Create clean URDF root
        urdf_root = ET.Element("robot")
        urdf_root.set("name", robot_name)

        # Copy all non-XACRO elements
        for child in processed_root:
            if not child.tag.startswith("xacro:"):
                urdf_root.append(child)

        # Format and return
        return self._format_urdf_xml(urdf_root)

    def _format_urdf_xml(self, root: ET.Element) -> str:
        """Format XML with proper indentation"""
        xml_str = ET.tostring(root, encoding="unicode")

        # Parse with minidom for pretty printing
        from xml.dom import minidom

        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")

        # Remove empty lines and fix formatting
        lines = [line for line in pretty_xml.split("\n") if line.strip()]

        # Replace the first line with proper XML declaration
        if lines and lines[0].startswith("<?xml"):
            lines[0] = '<?xml version="1.0"?>'

        return "\n".join(lines)

    def convert_file(
        self, input_file: str, output_file: str, robot_name: Optional[str] = None
    ) -> None:
        """
        Convert a XACRO file to URDF format

        Args:
            input_file: Path to input XACRO file
            output_file: Path to output URDF file
            robot_name: Name for the robot (extracted from XACRO if not provided)
        """
        import os

        # Get base path for includes
        base_path = os.path.dirname(input_file)

        # Read XACRO file
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                xacro_content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"XACRO file not found: {input_file}")
        except Exception as e:
            raise IOError(f"Error reading XACRO file: {e}")

        # Parse and process XACRO
        processed_root = self.parse_xacro(xacro_content, base_path)

        # Extract robot name if not provided
        if robot_name is None:
            robot_name = processed_root.get("name", "robot")

        # Generate URDF
        urdf_content = self.generate_urdf(robot_name, processed_root)

        # Write URDF file
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(urdf_content)
        except Exception as e:
            raise IOError(f"Error writing URDF file: {e}")

    def convert_string(
        self, xacro_content: str, robot_name: Optional[str] = None
    ) -> str:
        """
        Convert XACRO content string to URDF format

        Args:
            xacro_content: XACRO content as string
            robot_name: Name for the robot (extracted from XACRO if not provided)

        Returns:
            URDF content as string
        """
        # Parse and process XACRO
        processed_root = self.parse_xacro(xacro_content)

        # Extract robot name if not provided
        if robot_name is None:
            robot_name = processed_root.get("name", "robot")

        # Generate and return URDF
        return self.generate_urdf(robot_name, processed_root)


@dataclass
class ConverterArgs:
    """Command-line arguments for the URDF <-> XACRO converter"""

    input_file: str
    """Input file path (URDF or XACRO)"""

    output: Optional[str] = None
    """Output file path (auto-detected if not specified)"""

    name: Optional[str] = None
    """Robot name (default: extracted from input file)"""

    mode: Literal["auto", "urdf2xacro", "xacro2urdf"] = "auto"
    """Conversion mode (default: auto-detect from file extension)"""

    verbose: bool = False
    """Enable verbose output"""


def main():
    """Command-line interface for the URDF <-> XACRO converter"""
    import os

    args = tyro.cli(ConverterArgs, description="Convert between URDF and XACRO formats")

    # Determine conversion mode
    input_ext = os.path.splitext(args.input_file)[1].lower()

    if args.mode == "auto":
        if input_ext == ".urdf":
            mode = "urdf2xacro"
        elif input_ext == ".xacro":
            mode = "xacro2urdf"
        else:
            print(
                f"Error: Cannot auto-detect conversion mode for file extension '{input_ext}'"
            )
            print("Please specify --mode explicitly or use .urdf/.xacro extensions")
            return 1
    else:
        mode = args.mode

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(args.input_file)[0]
        if mode == "urdf2xacro":
            output_file = f"{base_name}.xacro"
        else:  # xacro2urdf
            output_file = f"{base_name}.urdf"

    # Convert file
    try:
        if mode == "urdf2xacro":
            converter = URDFToXacroConverter()
            converter.convert_file(args.input_file, output_file, args.name)

            if args.verbose:
                print(
                    f"Successfully converted URDF to XACRO: {args.input_file} -> {output_file}"
                )
                print(
                    f"Found {len(converter.links)} links and {len(converter.joints)} joints"
                )

        else:  # xacro2urdf
            converter = XacroToURDFConverter()
            converter.convert_file(args.input_file, output_file, args.name)

            if args.verbose:
                print(
                    f"Successfully converted XACRO to URDF: {args.input_file} -> {output_file}"
                )
                print(
                    f"Processed {len(converter.properties)} properties and {len(converter.macros)} macros"
                )

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
