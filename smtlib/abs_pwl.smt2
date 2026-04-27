(assert
    (forall ((x Real))
    (forall ((z Real))
        (=> (and (=> (< x 0) (= (+ z x) 0))
                 (=> (>= x 0) (= (- z x) 0)))
            (>= z 0)))))
