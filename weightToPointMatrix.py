import c4d
import sys

def deleteSkinData(obj):

    for tag in obj.GetTags():
        if (tag.CheckType(c4d.Tweights) or
            tag.CheckType(c4d.Tposemorph)):
            doc.AddUndo(c4d.UNDOTYPE_DELETE, tag)
            tag.Remove()

    for child in obj.GetChildren():
        if (child.CheckType(c4d.Oskin) or
            child.CheckType(1019768)):
            doc.AddUndo(c4d.UNDOTYPE_DELETE, child)
            child.Remove()

# -----------------------------------------------
if sys.version_info.major == 2:
    class dict(dict):
        def items(self):
            return super(dict, self).iteritems()
    range = xrange
# -----------------------------------------------
def getAllObjs(obj=None, objs=None):
    if objs is None: objs = []
    if obj  is None: obj = doc.GetFirstObject()

    while obj:
        objs.append(obj)
        if obj.GetDown():
            getAllObjs(obj.GetDown(), objs)
        obj = obj.GetNext()
    return objs


def getPoints(obj):
    return [index
    for index, _ in enumerate(obj.GetPointS().GetAll(obj.GetPointCount()))]

def getPointsPos(obj, points):
    return [obj.GetPoint(point) * obj.GetMg()
            for point, _ in enumerate(points)]

def getJointsData(obj, points):

    weightTag = obj.GetTag(c4d.Tweights)
    if weightTag is None:
        c4d.gui.MessageDialog('The selected object has no weight tag!')
        return

    weightData = []
    jointGuids = []
    for joint in range(weightTag.GetJointCount()):
        jointGuid = weightTag.GetJoint(joint, doc).GetGUID()
        jointGuids.append(jointGuid)
        _ = []
        for point in points:
            pointWeight = weightTag.GetWeight(joint, point)
            _.append(pointWeight)
        weightData.append(_)
    return jointGuids, weightData

def addXpresso(obj):
    doc.StartUndo()
    deleteSkinData(obj)
    xpTag = obj.MakeTag(1001149)
    doc.AddUndo(c4d.UNDOTYPE_NEW, xpTag)
    doc.EndUndo()
    master = xpTag.GetNodeMaster()
    root = master.GetRoot()
    return master, root

def main():
    baseObjs = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_CHILDREN)
    if not baseObjs:
        return

    allObjs = getAllObjs()

    for obj in baseObjs:

        points              = getPoints(obj)
        jointGuids, weights = getJointsData(obj, points)
        pointPoss           = getPointsPos(obj, points)
        # ---------------------------------------------------------------
        joints = [_obj for guid in jointGuids for _obj in allObjs if _obj.GetGUID() == guid]

        # create xptag
        master, root = addXpresso(obj)
        objNode = master.CreateNode(root, c4d.ID_OPERATOR_OBJECT, x=100, y=400)
        objNode[c4d.GV_OBJECT_OBJECT_ID] = obj
        objNode.AddPort(c4d.GV_PORT_OUTPUT, c4d.GV_OBJECT_OPERATOR_OBJECT_OUT)
        mathNodeDic = {}
        for joint, weight in zip(joints, weights):

            jointNode = master.CreateNode(root, c4d.ID_OPERATOR_OBJECT, x=100, y=200)
            jointNode[c4d.GV_OBJECT_OBJECT_ID] = joint
            jointNode.AddPort(c4d.GV_PORT_OUTPUT, c4d.GV_OBJECT_OPERATOR_GLOBAL_OUT)

            for i in points:
                if weight[i] == 0.0:
                    continue
                # create matrixMultVecNode
                localPos = ~joint.GetMg() * pointPoss[i]

                matrixMultVecNode = master.CreateNode(root, c4d.ID_OPERATOR_MATRIXMULVECTOR, x=200, y=200)
                matrixMultVecNode[c4d.GV_MATRIXMULVECT_INPUT2] = localPos
                jointNode.GetOutPort(0).Connect(matrixMultVecNode.GetInPort(0))


                # create float mathNode
                floatMathNode = master.CreateNode(root, c4d.ID_OPERATOR_FLOATMATH, x=300, y=200)
                floatMathNode[c4d.GV_DYNAMIC_DATATYPE] = 23
                floatMathNode[c4d.GV_FLOATMATH_FUNCTION_ID] = 2
                floatMathNode[c4d.GV_FLOATMATH_REAL] = weight[i]
                matrixMultVecNode.GetOutPort(0).Connect(floatMathNode.GetInPort(0))

                # create PointNode
                pointNode = master.CreateNode(root, c4d.ID_OPERATOR_POINT, x=700, y=200)
                pointNode[c4d.GV_POINT_USE_DEFORMED] = 1
                pointNode[c4d.GV_POINT_MODE] = 100
                pointNode[c4d.GV_POINT_INPUT_POINT] = i
                pointNode.AddPort(c4d.GV_PORT_INPUT, c4d.GV_POINT_INPUT_POSITION)


                # create math Node
                mathNode = mathNodeDic.get(i)
                if mathNode is None:
                    mathNode = master.CreateNode(root, c4d.ID_OPERATOR_MATH, x=500, y=200)
                    mathNode[c4d.GV_DYNAMIC_DATATYPE] = 23
                    mathNodeDic[i] = mathNode

                    floatMathNode.GetOutPort(0).Connect(mathNode.GetInPort(0))
                else:
                    portRange = mathNode.GetInPortCount()
                    mathNode.AddPort(c4d.GV_PORT_INPUT,  c4d.DescID(c4d.DescLevel(2000,1002)))
                    floatMathNode.GetOutPort(0).Connect(mathNode.GetInPort(portRange-1))

                mathNode.GetOutPort(0).Connect(pointNode.GetInPort(2))

                objNode.GetOutPort(0).Connect(pointNode.GetInPort(0))
                # -------------------------------------
    c4d.EventAdd()

if __name__ == '__main__':
    main()