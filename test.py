import Sofa

def createScene(root):
    """
    高质量软组织Demo - 高分辨率网格，优化的视觉效果
    保持稳定性，同时提供更好的视觉体验
    """
    
    # ======================================================
    # 1. 加载插件
    # ======================================================
    root.addObject('RequiredPlugin', name='SofaPython3')
    plugins = [
        'Sofa.Component.AnimationLoop',
        'Sofa.Component.Collision.Detection.Algorithm',
        'Sofa.Component.Collision.Detection.Intersection',
        'Sofa.Component.Collision.Geometry',
        'Sofa.Component.Collision.Response.Contact',
        'Sofa.Component.Constraint.Lagrangian.Correction',
        'Sofa.Component.Constraint.Lagrangian.Solver',
        'Sofa.Component.Constraint.Projective',
        'Sofa.Component.Controller',
        'Sofa.Component.LinearSolver.Direct',
        'Sofa.Component.Mass',
        'Sofa.Component.ODESolver.Backward',
        'Sofa.Component.SolidMechanics.FEM.Elastic',
        'Sofa.Component.StateContainer',
        'Sofa.Component.Topology.Container.Grid',
        'Sofa.Component.Visual',
        'Sofa.GL.Component.Rendering3D',
        'Sofa.GUI.Component',
    ]
    for plugin in plugins:
        root.addObject('RequiredPlugin', name=plugin)

    # ======================================================
    # 2. 全局设置 - 最保守的配置
    # ======================================================
    root.addObject('VisualStyle', displayFlags='showVisualModels showBehaviorModels showCollisionModels')
    root.gravity = [0, -9.81, 0]
    root.dt = 0.005  # 较小的步长，提高稳定性
    
    # 使用DefaultAnimationLoop，避免初始化问题
    root.addObject('DefaultAnimationLoop')
    
    # 约束求解器 - 关键：大量迭代，宽松容差
    root.addObject('GenericConstraintSolver', 
                   maxIterations=2000,       # 非常多的迭代
                   tolerance=1e-2)            # 非常宽松的容差

    # ======================================================
    # 2.1 鼠标交互配置说明
    # ======================================================
    # 注意：MouseManager是GUI内部管理的组件，无法在Python场景中直接配置
    # 请在GUI中手动设置：View -> MouseManager -> Left Button -> Stiffness = 5
    # 
    # 或者，您可以在SOFA的配置文件中设置默认值：
    # 编辑 ~/.sofa/config/loadedPlugins.ini 或相关配置文件
    #
    # 推荐的Stiffness值：5-20（值越小越柔和，但跟随性会降低）

    # ======================================================
    # 3. 碰撞检测
    # ======================================================
    root.addObject('CollisionPipeline', name='pipeline')
    root.addObject('BruteForceBroadPhase')
    root.addObject('BVHNarrowPhase')
    root.addObject('MinProximityIntersection', 
                   alarmDistance=0.03, 
                   contactDistance=0.01)
    
    # 使用PenalityContactForceField，更简单稳定
    root.addObject('DefaultContactManager', 
                   response='PenalityContactForceField',
                   responseParams='penalty=50')  # 非常小的penalty

    # ======================================================
    # 4. 创建柔性体
    # ======================================================
    softBody = root.addChild('SoftBody')
    
    # 4.1 求解器 - 调整阻尼，允许形变但保持稳定
    softBody.addObject('EulerImplicitSolver', 
                       name='odesolver',
                       rayleighStiffness=0.4,  # 适中的阻尼，允许形变
                       rayleighMass=0.4)        # 适中的阻尼
    # 使用标准线性求解器（移除模板参数，使用默认配置更稳定）
    softBody.addObject('SparseLDLSolver', name='linearSolver')
    
    # 4.2 拓扑 - 高分辨率网格，提供更好的视觉效果
    softBody.addObject('RegularGridTopology', 
                       name='grid',
                       n=[10, 10, 15],          # 高分辨率网格
                       min=[-1, -1, 0],
                       max=[1, 1, 6])            # 更大的尺寸，更美观
    
    # 4.3 力学对象
    softBody.addObject('MechanicalObject', name='dofs')
    
    # 4.4 约束校正 - 关键！使用UncoupledConstraintCorrection
    # 设置合适的compliance，既柔和又允许形变
    softBody.addObject('UncoupledConstraintCorrection', 
                       defaultCompliance=0.05)  # 合适的compliance，允许形变但保持稳定
    
    # 4.5 质量 - 根据新的尺寸调整质量
    softBody.addObject('UniformMass', totalMass=20.0)
    
    # 4.6 力场 - 软组织材质参数
    softBody.addObject('HexahedronFEMForceField',
                       youngModulus=80,        # 软组织典型的杨氏模量
                       poissonRatio=0.45,      # 接近不可压缩（软组织特性）
                       method='large')

    # ======================================================
    # 5. 碰撞模型 - 关键：极小的接触刚度
    # ======================================================
    softBody.addObject('TriangleCollisionModel', 
                       contactStiffness=1)     # 极小的刚度
    softBody.addObject('LineCollisionModel', 
                       contactStiffness=1)
    softBody.addObject('PointCollisionModel', 
                       contactStiffness=1)

    # ======================================================
    # 6. 固定约束 - 关键：添加足够的约束防止秩不足
    # ======================================================
    # 固定顶部区域（扩大固定区域，确保有足够的约束点）
    softBody.addObject('BoxROI', 
                       name='fixedBox',
                       box=[-1.1, -1.1, 5.2, 1.1, 1.1, 6.1],  # 扩大固定区域
                       drawBoxes=True)
    softBody.addObject('FixedConstraint', 
                       indices='@fixedBox.indices')
    
    # 额外固定底部的一个点，防止刚体运动
    # 这确保系统有足够的约束来求解
    softBody.addObject('BoxROI', 
                       name='bottomFix',
                       box=[-0.1, -0.1, 0, 0.1, 0.1, 0.2],  # 固定底部中心点
                       drawBoxes=False)
    softBody.addObject('FixedConstraint', 
                       indices='@bottomFix.indices')

    # ======================================================
    # 7. 视觉模型 - 优化的视觉效果
    # ======================================================
    vis = softBody.addChild('Visual')
    
    # 视觉模型需要自己的拓扑（用于OglModel获取连接信息）
    vis.addObject('RegularGridTopology', 
                  name='visualGrid',
                  n=[10, 10, 15],
                  min=[-1, -1, 0],
                  max=[1, 1, 6])
    
    # 视觉模型的力学对象（用于接收变形后的位置）
    vis.addObject('MechanicalObject', name='visualDOFs')
    
    # OglModel使用视觉拓扑和视觉力学对象
    vis.addObject('OglModel', 
                  src='@visualDOFs',               # 使用视觉力学对象的位置
                  color=[0.9, 0.6, 0.7, 0.9],      # 柔和的粉红色，类似软组织
                  wireframe=False,                  # 实体渲染
                  edges=False)                      # 不显示边线
    
    # 关键：使用IdentityMapping将父节点力学对象的变形映射到视觉模型
    # 这确保视觉模型完全同步跟随力学对象的变形
    vis.addObject('IdentityMapping', 
                  input='@../dofs',                # 输入：父节点的力学对象
                  output='@visualDOFs')            # 输出：视觉模型的力学对象
    
    return root
