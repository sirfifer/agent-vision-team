import * as assert from 'assert';
import { MemoryTreeProvider } from '../providers/MemoryTreeProvider';
import { Entity } from '../models/Entity';

suite('MemoryTreeProvider Test Suite', () => {
  let provider: MemoryTreeProvider;

  setup(() => {
    provider = new MemoryTreeProvider();
  });

  test('should start with empty entities', () => {
    const children = provider.getChildren();
    assert.strictEqual(children.length, 3); // 3 tier groups
  });

  test('should group entities by tier', () => {
    const visionEntity: Entity = {
      name: 'test_vision',
      entityType: 'vision_standard',
      observations: ['protection_tier: vision', 'All tests must pass'],
      relations: [],
    };

    const archEntity: Entity = {
      name: 'test_arch',
      entityType: 'pattern',
      observations: ['protection_tier: architecture', 'Use DI pattern'],
      relations: [],
    };

    const qualityEntity: Entity = {
      name: 'test_quality',
      entityType: 'component',
      observations: ['protection_tier: quality', 'Needs refactoring'],
      relations: [],
    };

    provider.updateEntities([visionEntity, archEntity, qualityEntity]);

    const tierGroups = provider.getChildren();
    assert.strictEqual(tierGroups.length, 3);

    // Vision tier should have 1 entity
    const visionChildren = provider.getChildren(tierGroups[0]);
    assert.strictEqual(visionChildren.length, 1);

    // Architecture tier should have 1 entity
    const archChildren = provider.getChildren(tierGroups[1]);
    assert.strictEqual(archChildren.length, 1);

    // Quality tier should have 1 entity
    const qualityChildren = provider.getChildren(tierGroups[2]);
    assert.strictEqual(qualityChildren.length, 1);
  });

  test('should handle entities without tier', () => {
    const entity: Entity = {
      name: 'no_tier',
      entityType: 'component',
      observations: ['Some observation without tier'],
      relations: [],
    };

    provider.updateEntities([entity]);

    const tierGroups = provider.getChildren();
    // Entity without tier won't appear in any tier group
    const visionChildren = provider.getChildren(tierGroups[0]);
    const archChildren = provider.getChildren(tierGroups[1]);
    const qualityChildren = provider.getChildren(tierGroups[2]);

    assert.strictEqual(visionChildren.length, 0);
    assert.strictEqual(archChildren.length, 0);
    assert.strictEqual(qualityChildren.length, 0);
  });

  test('should update entities on refresh', () => {
    const entity1: Entity = {
      name: 'entity1',
      entityType: 'component',
      observations: ['protection_tier: quality', 'First entity'],
      relations: [],
    };

    provider.updateEntities([entity1]);
    let tierGroups = provider.getChildren();
    let qualityChildren = provider.getChildren(tierGroups[2]);
    assert.strictEqual(qualityChildren.length, 1);

    // Update with different entities
    const entity2: Entity = {
      name: 'entity2',
      entityType: 'component',
      observations: ['protection_tier: quality', 'Second entity'],
      relations: [],
    };

    provider.updateEntities([entity2]);
    tierGroups = provider.getChildren();
    qualityChildren = provider.getChildren(tierGroups[2]);
    assert.strictEqual(qualityChildren.length, 1);
  });
});
