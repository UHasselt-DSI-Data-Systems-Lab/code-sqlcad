(declare-fun F (Real Real) Real)

(assert
    (forall ((x Real))
    (exists ((y Real) (z Real))
        (and (> x 0)
            (= (F x y) 0)
            (< (+ x y -1) 0)
            (>= (+ (* 3.2 x) y) 0)
            (or (not (= z 0)) (= (- y z) 0))))))
