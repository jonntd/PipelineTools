import pymel.core as pm
import pymel.util as pu
import pymel.util.path as pp
import maya.cmds as cm
import maya.mel as mm
import shutil
import os
import random as rand
import PipelineTools.customClass as cc
from functools import wraps
reload(cc)
###misc function
###Rigging
def do_function_on_single(func):
    """wrap a function to operate on select object or object name string"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        sel = pm.selected()
        args_list = []
        for arg in args:
            if type(arg) == str:
                ob_found = pm.ls(arg)
                print ob_found
                if ob_found:
                    for ob in ob_found:
                        print ob
                        args_list.append(ob)
        #print args_list
        sel.extend(args_list)
        for ob in sel:
            func(ob, **kwargs)
    return wrapper

def do_function_on_set(func):
    """wrap a function to operate on select object or object name string"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        sel = pm.selected()
        args_list = []
        for arg in args:
            if type(arg) == str:
                ob_found = pm.ls(arg)
                print ob_found
                if ob_found:
                    for ob in ob_found:
                        print ob
                        args_list.append(ob)
        #print args_list
        sel.extend(args_list)
        result = func(sel, **kwargs)
        return result
    return wrapper

def do_function_on_setToLast(func):
    """wrap a function to operate on select object or object name string"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        sel = pm.selected()
        args_list = []
        for arg in args:
            if type(arg) == str:
                ob_found = pm.ls(arg)
                print ob_found
                if ob_found:
                    for ob in ob_found:
                        print ob
                        args_list.append(ob)
        #print args_list
        sel.extend(args_list)
        target = sel[-1]
        result = func(sel, target, **kwargs)
        return result
    return wrapper

@do_function_on_setToLast
def connect_joint(bones,boneRoot,**kwargs):
    for bone in bones:
        pm.connectJoint(bone, boneRoot, **kwargs)

@do_function_on_single
def reset_joint_orient(bone):
    if type(bone) != pm.nt.Joint:
        return
    attrList = ["jointOrientX", "jointOrientY", "jointOrientZ"]
    for at in attrList:
        bone.attr(at).set(0)

@do_function_on_single
def mirror_joint_tranform(bone, translate=False, rotate=True, **kwargs):
    #print bone
    opbone = get_opposite_joint(bone, customPrefix=(kwargs['customPrefix']if kwargs.has_key('customPrefix') else None))
    offset = 1
    if not opbone:
        opbone = bone
        offset = -1
        translate = False
    if all([type(b) == pm.nt.Joint for b in [bone, opbone]]):
        if rotate:
            pm.joint(opbone, edit=True, ax=pm.joint(bone, q=True, ax=True),
                     ay=pm.joint(bone, q=True, ay=True)*offset,
                     az=pm.joint(bone, q=True, az=True)*offset)
        if translate:
            bPos = pm.joint(bone, q=True, p=True)
            pm.joint(opbone, edit=True, p=(bPos[0]*-1, bPos[1], bPos[2]),
                     ch=kwargs['ch'] if kwargs.has_key('ch') else False,
                     co=not kwargs['ch'] if kwargs.has_key('ch') else True)

#@do_function_on
def get_opposite_joint(bone, select=False, opBoneOnly=True, customPrefix=None):
    "get opposite Bone"
    mirrorPrefixes_list = [
        ('Left', 'Right'),
        ('_L_', '_R_')
    ]
    try:
        if all(customPrefix, type(customPrefix) == tuple, len(customPrefix) == 2):
            mirrorPrefixes_list.append(customPrefix)
    except:
        pass
    for mirrorprefix in mirrorPrefixes_list:
        for index,mp in enumerate(mirrorprefix):
            if mp in bone.name():
                opBoneName = bone.name().replace(mirrorprefix[index], mirrorprefix[index-1])
                opBone = pm.ls(opBoneName)[0] if pm.ls(opBoneName) else None
                if select:
                    if opBoneOnly:
                        pm.select(opBone)
                    else:
                        pm.select(bone, opBone)
                print opBoneName
                return opBone

def reset_bindPose():
    newbp = pm.dagPose(bp=True, save=True)
    bindPoses = pm.ls(type=pm.nt.DagPose)
    for bp in bindPoses:
        if bp != newbp:
            pm.delete(bp)

###function
def exportCam():
    '''export allBake Camera to FBX files'''
    FBXSettings = [
        "FBXExportBakeComplexAnimation -v true;"
        "FBXExportCameras -v true;"
        "FBXProperty Export|AdvOptGrp|UI|ShowWarningsManager -v false;"
        "FBXProperty Export|AdvOptGrp|UI|GenerateLogData -v false;"
    ]
    for s in FBXSettings:
        mm.eval(s)
    excludedList = ['frontShape', 'sideShape', 'perspShape', 'topShape']
    cams = [
        (cam, pm.listTransforms(cam)[0])
        for cam in pm.ls(type='camera') if str(cam.name()) not in excludedList]
    scenePath = [str(i) for i in pm.sceneName().split("/")]
    stripScenePath = scenePath[:-1]
    sceneName = scenePath[-1]
    print sceneName
    filename = "_".join([sceneName[:-3], 'ConvertCam.fbx'])
    stripScenePath.append(filename)
    filePath = "/".join(stripScenePath)
    for c in cams:
        pm.select(c[1])
        oldcam = c[1]
        newcam = pm.duplicate(oldcam, rr=True)[0]
        startFrame = int(pm.playbackOptions(q=True, minTime=True))
        endFrame = int(pm.playbackOptions(q=True, maxTime=True))
        pm.parent(newcam, w=True)
        for la in pm.listAttr(newcam, l=True):
            attrName = '.'.join([newcam.name(), str(la)])
            pm.setAttr(attrName, l=False)
        camconstraint = pm.parentConstraint(oldcam, newcam)
        pm.bakeResults(newcam, at=('translate', 'rotate'), t=(startFrame, endFrame), sm=True)
        pm.delete(camconstraint)
        pm.select(newcam, r=True)
        cc = 'FBXExport -f "%s" -s' % filePath
        mm.eval(cc)

@do_function_on_single
def mirror_transform(obs, axis="x",xform=[0,4]):
    if not obs:
        print "no object to mirror"
        return
    axisDict = {
        "x":('tx', 'ry', 'rz', 'sx'),
        "y":('ty', 'rx', 'rz', 'sy'),
        "z":('tz', 'rx', 'ry', 'sz')}
    #print obs
    if type(obs) != list:
        obs = [obs]
    for ob in obs:
        if type(ob) == pm.nt.Transform:
            for at in axisDict[axis][xform[0]:xform[1]]:
                ob.attr(at).set(ob.attr(at).get()*-1)

@do_function_on_set
def lockTransform(obs,lock=True):
    for ob in obs:
        for at in ['translate','rotate','scale']:
            ob.attr(at).set(lock=lock)

@do_function_on_single
def addVrayOpenSubdivAttr(ob):
    '''add Vray OpenSubdiv attr to enable smooth mesh render'''
    if str(pm.getAttr('defaultRenderGlobals.ren')) == 'vray':
        obShape = ob.getShape()
        pm.vray('addAttributesFromGroup', obShape, "vray_opensubdiv", 1)
        pm.setAttr(obShape+".vrayOsdPreserveMapBorders", 2)

@do_function_on_single
def clean_attr(ob):
    '''clean all Attribute'''
    for atr in ob.listAttr():
        try:
            atr.delete()
            print "%s is deleted" % atr.name()
        except:
            pass
####
@do_function_on_set
def find_instance(obs,instanceOnly=True):
    allTransform = [tr for tr in pm.ls(type=pm.nt.Transform) if tr.getShape()]
    instanceShapes =[]
    if instanceOnly:
        pm.select(cl=True)
    for ob in obs:
        obShape = ob.getShape()
        if obShape.name().count('|'):
            obShapeName = obShape.name().split('|')[-1]
            for tr in allTransform:
                shape = tr.getShape()
                if obShapeName == shape.name().split('|')[-1] and tr != ob:
                    #pm.select(ob,add=True)
                    instanceShapes.append(tr)
        #else:
            #print "%s have no Instance Shape" % ob
    pm.select(instanceShapes,add=True)
    return instanceShapes

def loc42Curve():
    sel = pm.selected()
    if len(sel)>3:
        posList = [o.translate.get() for o in sel]
        pm.curve(p=posList)

def randU(offset=0.1):
    sel=pm.selected()
    if not sel:
        return
    for o in sel:
        pm.polyEditUV(o.map,u=rand.uniform(-offset,offset))

def mirrorUV(dir='Left'):
    if dir=='Left':
        pm.polyEditUV(u=-0.5)
    else:
        pm.polyEditUV(u=0.5)
    pm.polyFlipUV()

def rotateUV():
    sel=pm.selected()
    for o in sel:
        selShape=o.getShape()
        pm.select(selShape.map,r=1)
        pm.polyEditUV(rot=1,a=180,pu=0.5,pv=0.5)
    pm.select(sel,r=1)

def getInfo():
    sel= pm.selected()[0]
    if not sel:
        return
    print type(sel)
    for a in dir(sel):
        print str(a)+": "
        try:
            print eval('sel.%s.__module__\n' % a)
            #print eval('sel.%s.__method__\n' % a)
            print eval('sel.%s.__doc__\n' % a)
        except:
            continue
        print ("-"*100+"\n")*2

def send_current_file(drive='N', version=1, verbose=True):
    src = pm.sceneName()
    todayFolder = pm.date(f='YYMMDD')
    if version>1:
        todayFolder = "_".join([todayFolder,
                               ('%02d' % version)])
    dest = src.replace(drive+':',
                       '%s:/to/%s' % (drive, todayFolder))
    try:
        checkDir(dest)
        pm.sysFile(src, copy=dest)
        if verbose:
            print "%s copy to %s" % (src,dest)
    except (IOError, OSError) as why:
        print "Copy Error"
        print why

def GetAssetPath(Assetname, versionNum):
    ''' get AssetPath Relate to Character'''
    try:
        CH = cc.Character(Assetname)
    except:
        print "get Asset not possible"
        return
    CHPath = {}
    CHPath['_common'] = pp(CH.texCommon)
    try:
        CHversion = CH[versionNum-1]
        if CHversion.path.has_key('..'):
            CHHairFiles = pp(CHversion.path['hair']).files('*.mb')
            if CHHairFiles:
                CHHairFiles.sort(key=os.path.getmtime)
                CHPath['hair'] = CHHairFiles[-1]
            if CHversion.path.has_key('clothes'):
                CHClothFiles = pp(CHversion.path['clothes']).files('*.mb')
                if CHClothFiles:
                    CHClothFiles.sort(key=os.path.getmtime)
                    CHPath['cloth'] = CHClothFiles[-1]
                    # print "No folder 'clothes' in %s " % CH.path
            try:
                CHPath['clothRender'] = CHversion.path['clothRender']
                CHPath['hairRender'] = CHversion.path['hairRender']
            except:
                pass
                # print "No folder 'render' in %s " % CHversion.path['..']
        if CHversion.texPath.has_key('..'):
            CHPath['tex'] = CHversion.texPath['..']
            for k in ['pattern','uv','zbr']:
                try:
                    CHPath[k] = pp(CHversion.texPath[k])
                except:
                    pass
                    # print "no folder '%s' in %s " % (k, CHPath['tex'])
    except (IOError, OSError) as why:
        print "Character %s has no version or \n\%s" % (Assetname,why)
    return CHPath

def sendFile(CH,
             ver,
             num=0,
             destdrive="",
             sendFile={
                 'Send':False,
                 'hair':False,
                 'cloth':False,
                 'xgen':False,
                 'uv':False,
                 'zbr':False,
                 'tex':False,
                 'pattern':False,
                 '_common':False}):
    '''send NS57 File'''
    def getDest(pa):
        paSplit = pa.splitall()[1:]
        projectSplit = pm.workspace.path.splitall()[1:-2]
        return "/".join([element for element in paSplit
                         if element not in projectSplit])
    def doCop(fodPath):
        if destdrive:
            drive = destdrive+":"
        else:
            drive = fodPath.drive
        dest = os.path.normpath("/".join([
            drive,
            "to",
            todayFolder,
            getDest(fodPath)]))
        #print fodPath,'-->',dest
        sysCop(fodPath, dest)
    def sendDir(k):
        if AllPath.has_key(k):
            doCop(pp(AllPath[k]))
        else:
            print "no %s folder" % k

    def sendTexFile(k):
        def copFiles(fileList):
            for t in fileList:
                doCop(t)
        if AllPath.has_key(k):
            try:
                # texFiles = [f for f in os.listdir(AllPath[k])
                #             if (os.path.isfile(os.path.join(AllPath[k],f))
                #                 and CH in f)]
                # texPath = r'%s' % unicode(AllPath[k])
                # print os.listdir(texPath)
                texFiles = [f for f in pp(AllPath[k]).files()
                        if (any([f.endswith(c) for c in ['jpg',
                                                         'png',
                                                         'tif',
                                                         'tiff']])
                            and CH in f.basename())]
                if texFiles:
                    copFiles(texFiles)
                else:
                    print "no Texture Files"
                psdDir = [d for d in pp(AllPath[k]).dirs()
                          if 'psd' in d]
                if psdDir:
                    psdDir = psdDir[0]
                    psdFiles = [f for f in psdDir.files()
                                if(any([f.endswith(c) for c in ['psd', 'psb']])
                                and CH in f.basename())]
                    copFiles(psdFiles)
                else:
                    print "no Psd Files"
            except (IOError, OSError) as why:
                #print AllPath[k] 
                print why
        else:
            print "no %s folder" % k
    if sendFile['cloth']:
        sendFile['clothRender'] = True
    if sendFile['hair']:
        sendFile['hairRender'] = True
    if sendFile['Send'] == True:
        AllPath = GetAssetPath(CH, ver)
        #print AllPath
        todayFolder = pm.date(f='YYMMDD')
        if num and num != 1:
            todayFolder = "_".join([todayFolder, ('%02d' % num)])
        for key, value in sendFile.iteritems():
            if key == 'tex' or key == '_common':
                if value and key == 'tex':
                    sendTexFile('tex')
                if value and key == '_common':
                    sendTexFile('_common')
            elif key != 'Send':
                if value:
                    sendDir(key)

def checkDir(pa,force=True):
    if not os.path.exists(os.path.dirname(pa)):
        os.makedirs(os.path.dirname(pa))
    else:
        if force:
            if os.path.isdir(pa):
                shutil.rmtree(os.path.dirname(pa))
                os.makedirs(os.path.dirname(pa))
            elif os.path.isfile(pa):
                os.remove(pa)
        else:
            print "%s exists" % pa
    print "checked"


def sysCop(src, dest):
    checkDir(dest)
    try:
        if os.path.isdir(src):
            shutil.copytree(src,dest)
            print "copying " + dest
            for file in os.listdir(dest):
                if os.path.isdir(src+"/"+file):
                    print "%s folder Copied" % file
                else:
                    print "%s file Copied" % file
        elif os.path.isfile(src):
            shutil.copy(src,dest)
            print "%s copied" % dest
        else:
            print "%s does not exist" % src
    except (IOError,OSError,WindowsError) as why:
        print src
        print dest
        print "Copy error\n",why


def setTexture():
    for m in oHairSG:
        fileList=[file for file in m.listConnections()
                  if type(file)==pm.nodetypes.File]
    for f in fileList:
        for d in f.listAttr():
            try:
                if d.longName(fullPath=False).lower().endswith('texturename'):
                    print d,d.get()
                    d.set(d.get().replace('KG','IB'))
                    print d.get()
            except:
                continue