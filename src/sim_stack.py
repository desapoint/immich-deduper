from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class StackUnit:
	groupId: int
	ownerId: str
	assets: List[Any] = field(default_factory=list)
	coverAutoId: Optional[int] = None

	@property
	def primary(self) -> Any:
		if self.coverAutoId is not None:
			return next(asset for asset in self.assets if asset.autoId == self.coverAutoId)
		return self.assets[0]


@dataclass
class StackVisualGroup:
	groupId: int
	assets: List[Any] = field(default_factory=list)
	selected: List[Any] = field(default_factory=list)
	others: List[Any] = field(default_factory=list)
	stacks: List[StackUnit] = field(default_factory=list)


@dataclass
class StackPlan:
	groups: List[StackVisualGroup] = field(default_factory=list)

	@property
	def stacks(self) -> List[StackUnit]:
		return [stack for group in self.groups for stack in group.stacks]

	@property
	def assets(self) -> List[Any]:
		return [asset for group in self.groups for asset in group.assets]

	@property
	def selected(self) -> List[Any]:
		return [asset for group in self.groups for asset in group.selected]

	@property
	def others(self) -> List[Any]:
		return [asset for group in self.groups for asset in group.others]

	@property
	def coverIds(self) -> List[int]:
		return [stack.coverAutoId for stack in self.stacks if stack.coverAutoId is not None]


def _singleGroupId(assets: List[Any]) -> int:
	first = assets[0]
	return first.vw.muodId if first.vw.muodId is not None else first.autoId


def groupAssets(assets: List[Any], multiMode: bool) -> dict[int, List[Any]]:
	groups: dict[int, List[Any]] = {}
	if not assets: return groups

	singleGroupId = _singleGroupId(assets)
	for asset in assets:
		groupId = (asset.vw.muodId or 0) if multiMode else singleGroupId
		groups.setdefault(groupId, []).append(asset)
	return groups


def _matchingGroupId(grouped: dict[int, List[Any]], targetGroupId: int) -> Optional[int]:
	return next((groupId for groupId in grouped if str(groupId) == str(targetGroupId)), None)


def assetsForGroup(assets: List[Any], multiMode: bool, targetGroupId: Optional[int] = None) -> List[Any]:
	if targetGroupId is None: return list(assets)

	grouped = groupAssets(assets, multiMode)
	matchingId = _matchingGroupId(grouped, targetGroupId)
	if matchingId is None: raise ValueError(f"Group {targetGroupId} is no longer available")
	return grouped[matchingId]


def removeHandled(
	assets: List[Any],
	selectedIds: List[int],
	handledAssets: List[Any],
) -> tuple[List[Any], List[int]]:
	handledIds = {asset.autoId for asset in handledAssets}
	remainingAssets = [asset for asset in assets if asset.autoId not in handledIds]
	remainingSelectedIds = [autoId for autoId in selectedIds if autoId not in handledIds]
	return remainingAssets, remainingSelectedIds


def orderExistingStackIds(
	selectedAssetIds: List[str],
	stackByAsset: dict[str, str],
	primaryStacksByAsset: dict[str, List[str]],
) -> List[str]:
	ordered = []
	for assetId in selectedAssetIds:
		stackId = stackByAsset.get(assetId)
		if stackId and stackId not in ordered: ordered.append(stackId)
		for primaryStackId in sorted(primaryStacksByAsset.get(assetId, [])):
			if primaryStackId not in ordered: ordered.append(primaryStackId)
	return ordered


def splitUnselectedByStackMembership(
	assets: List[Any],
	stackMemberIds: set[str],
) -> tuple[List[Any], List[Any]]:
	deletable = [asset for asset in assets if asset.id not in stackMemberIds]
	protected = [asset for asset in assets if asset.id in stackMemberIds]
	return deletable, protected


def applyStackMetadata(
	assets: List[Any],
	stackResults: List[tuple[str, str, List[str]]],
):
	byMemberId = {}
	for stackId, primaryId, memberIds in stackResults:
		for memberId in memberIds: byMemberId[memberId] = (stackId, primaryId, memberIds)

	for asset in assets:
		stackInfo = byMemberId.get(asset.id)
		if not stackInfo or asset.ex is None: continue
		stackId, primaryId, memberIds = stackInfo
		asset.ex.stackId = stackId
		asset.ex.stackPrimaryAssetId = primaryId
		asset.ex.stackAssets = list(memberIds)


def commonStackId(assets: List[Any]) -> Optional[str]:
	stackIds = {asset.ex.stackId if asset.ex else None for asset in assets}
	if len(stackIds) != 1 or None in stackIds: return None
	return next(iter(stackIds))


def fullyStackedGroupAssets(plan: StackPlan) -> tuple[List[Any], List[int]]:
	assets = []
	groupIds = []
	for group in plan.groups:
		if commonStackId(group.assets):
			assets.extend(group.assets)
			groupIds.append(group.groupId)
	return assets, groupIds


def buildPlan(
	assets: List[Any],
	selectedIds: List[int],
	multiMode: bool,
	targetGroupId: Optional[int] = None,
	coverIds: Optional[List[int]] = None,
) -> StackPlan:
	if not assets: raise ValueError("No current assets to stack")

	selectedSet = set(selectedIds or [])
	coverSet = set(coverIds or [])
	if not selectedSet: raise ValueError("Select at least two assets in a group")

	grouped = groupAssets(assets, multiMode)
	if targetGroupId is not None:
		matchingId = _matchingGroupId(grouped, targetGroupId)
		if matchingId is None: raise ValueError(f"Group {targetGroupId} is no longer available")
		grouped = {matchingId: grouped[matchingId]}
	else:
		currentIds = {asset.autoId for asset in assets}
		missingIds = selectedSet - currentIds
		if missingIds: raise ValueError("The selection changed; select the assets again")

	plan = StackPlan()
	for groupId, groupAssetsList in grouped.items():
		selected = [asset for asset in groupAssetsList if asset.autoId in selectedSet]
		if not selected: continue

		ownerGroups: dict[str, List[Any]] = {}
		for asset in selected:
			if not asset.ownerId:
				raise ValueError(f"Asset #{asset.autoId} has no Immich owner and cannot be stacked")
			ownerGroups.setdefault(asset.ownerId, []).append(asset)

		stacks = []
		for ownerId, ownerAssets in ownerGroups.items():
			if len(ownerAssets) < 2:
				raise ValueError(
					f"Stacking requires at least two selected images for owner {ownerId} in group {groupId}"
				)
			chosenCovers = [asset.autoId for asset in ownerAssets if asset.autoId in coverSet]
			if len(chosenCovers) > 1:
				raise ValueError(f"Choose only one stack cover for owner {ownerId} in group {groupId}")
			stacks.append(StackUnit(
				groupId=groupId,
				ownerId=ownerId,
				assets=ownerAssets,
				coverAutoId=chosenCovers[0] if chosenCovers else None,
			))

		selectedAutoIds = {asset.autoId for asset in selected}
		plan.groups.append(StackVisualGroup(
			groupId=groupId,
			assets=groupAssetsList,
			selected=selected,
			others=[asset for asset in groupAssetsList if asset.autoId not in selectedAutoIds],
			stacks=stacks,
		))

	if not plan.groups: raise ValueError("Select at least two assets in a group")
	return plan
