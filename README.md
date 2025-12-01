# What are the components

1. Polycurve_CSG library (building on polyline_rs building on cavalier contours)

2. Migumi 
    1. Representation Maths:
        Optimization
            Torch Compute
        Visualizer
            Requires Shader parser Frontend
            Backend. 



1. Create the new expressions. Write the parser for this. 

2. Convert old data into new format. 

3. Then consider how to write the optimization loop.

4. Consider how to mesh with ASMBLR and the front end port. 

5. New stuff:
    1. PolyArc Will miss parts based on morphological skeleton displacement. Optimization to fix. 
    2. Two-way optimization to fix. 
    3. Curve limitation optiimization.
