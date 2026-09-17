Attribute VB_Name = "modODataCatalog"
Option Explicit

Public Function WorkOrderHeaderRelations() As Variant
    WorkOrderHeaderRelations = Array( _
        Array("WorkOrderOperationsSet", "WorkOrderOperations"), _
        Array("Objects", "WorkOrderObjects"), _
        Array("Status", "WorkOrderStatus"), _
        Array("Partners", "WorkOrderPartners"), _
        Array("PMNotification", "PMNotifications"), _
        Array("Attachment", "Attachment"), _
        Array("Permit", "Permit"), _
        Array("TaskListItems", "TaskListItems"), _
        Array("WorkOrderControlRooms", "WorkOrderControlRooms"), _
        Array("WorkOrderSafetyInformation", "WorkOrderSafetyInformation") _
    )
End Function

Public Function WorkOrderCoreSheets() As Variant
    WorkOrderCoreSheets = Array( _
        "WorkOrderHeader", _
        "WorkOrderOperations", _
        "WorkOrderOperationLongText", _
        "WorkOrderObjects", _
        "WorkOrderStatus", _
        "WorkOrderPartners", _
        "PMNotifications", _
        "Attachment", _
        "Permit", _
        "TaskListItems", _
        "WorkOrderControlRooms", _
        "WorkOrderSafetyInformation" _
    )
End Function

