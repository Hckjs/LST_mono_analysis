import numpy as np
import tables as tb
import click

@click.command()
@click.argument('infile', type=click.Path(exists=True, dir_okay=False))
def main(infile):
    with tb.open_file(infile, mode='a') as file:
        para_table = file.root['/dl1/event/telescope/parameters/tel_001']
        for row in range(len(para_table)):
            if (row % 5000) == 0:
                print(row)
            para_table.cols.hillas_phi[row] = np.rad2deg(para_table.cols.hillas_phi[row])
            para_table.cols.hillas_psi[row] = np.rad2deg(para_table.cols.hillas_psi[row])

if __name__ == '__main__':
    main()
