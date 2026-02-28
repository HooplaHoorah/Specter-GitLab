from typing import Type, TypeVar, Dict, Any, List, Optional
import uuid

T = TypeVar('T', bound='Component')

class Component:
    """Base class for all components."""
    pass

class Entity:
    """An entity is just an ID with a collection of components."""
    def __init__(self, entity_id: Optional[str] = None):
        self.id = entity_id or str(uuid.uuid4())
        self._components: Dict[Type[Component], Component] = {}

    def add_component(self, component: Component) -> None:
        self._components[component.__class__] = component

    def get_component(self, component_type: Type[T]) -> Optional[T]:
        # Pyre needs us to cast this explicitly or just suppress, but basic cast also works
        comp = self._components.get(component_type) # type: ignore
        return comp if comp is not None else None # type: ignore

    def has_component(self, component_type: Type[Component]) -> bool:
        return component_type in self._components

class System:
    """Base class for systems that process entities with specific components."""
    def __init__(self):
        self.world: Optional['World'] = None

    def update(self) -> None:
        """Called every tick or event cycle."""
        pass

class World:
    """The container for all entities and systems, acting as the 'Scene'."""
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.systems: List[System] = []

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)

    def add_system(self, system: System) -> None:
        system.world = self
        self.systems.append(system)

    def tick(self) -> None:
        """Runs all systems."""
        for system in self.systems:
            system.update()

    def get_entities_with_components(self, *component_types: Type[Component]) -> List[Entity]:
        """Query for entities that contain all the specified components."""
        matches = []
        for entity in self.entities.values():
            if all(entity.has_component(ct) for ct in component_types):
                matches.append(entity)
        return matches
