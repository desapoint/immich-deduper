from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class StackUnit:
	groupId: int
	ownerId: str
	assets: List[Any] = field(default_factory=list)

	@property
	def primary(self) -> Any:
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


def buildPlan(
	assets: List[Any],
	selectedIds: List[int],
	multiMode: bool,
	targetGroupId: Optional[int] = None,
) -> StackPlan:
	if not assets: raise ValueError("No current assets to stack")

	selectedSet = set(selectedIds or [])
	if not selectedSet: raise ValueError("Select at least two assets in a group")

	grouped = groupAssets(assets, multiMode)
	if targetGroupId is not None:
		matchingId = next((groupId for groupId in grouped if str(groupId) == str(targetGroupId)), None)
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
					f"Group {groupId} needs at least two selected assets for each Immich owner"
				)
			stacks.append(StackUnit(groupId=groupId, ownerId=ownerId, assets=ownerAssets))

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
